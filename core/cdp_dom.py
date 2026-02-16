"""
CDP-Level DOM Processing for BrowserAgent.

Uses Chrome DevTools Protocol (CDP) for richer, more reliable element discovery
than standard Playwright JS-based selectors. Captures:
- Accessibility tree (semantic roles, names, values)
- DOMSnapshot with computed styles and bounding boxes
- Shadow DOM elements
- Iframe content

Falls back to Playwright API when CDP is unavailable (non-Chromium browsers).
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import Page
from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class CDPElement:
    """Unified element representation combining CDP + Accessibility data."""
    
    # Identity
    node_id: int = 0                    # Backend node ID for CDP interaction
    tag_name: str = ""
    
    # Semantics (from Accessibility Tree)
    role: str = ""                      # ARIA role (button, link, textbox, etc.)
    name: str = ""                      # Accessible name
    
    # Content
    text: str = ""                      # Visible text content
    value: str = ""                     # Current value (inputs)
    
    # Attributes
    attributes: Dict[str, str] = field(default_factory=dict)
    
    # Geometry
    bounds: Dict[str, float] = field(default_factory=dict)  # x, y, width, height
    
    # State
    is_visible: bool = True
    is_interactive: bool = False
    is_focused: bool = False
    is_disabled: bool = False
    
    # Context
    selector: str = ""                  # Best CSS selector (Playwright fallback)
    shadow_root: bool = False           # Inside shadow DOM
    iframe_context: str = ""            # Iframe source if inside iframe
    
    # Matching
    index: int = 0                      # Element index in the list
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format compatible with element_finder expectations."""
        return {
            "tagName": self.tag_name,
            "text": self.text,
            "type": self.attributes.get("type", ""),
            "placeholder": self.attributes.get("placeholder", ""),
            "value": self.value,
            "id": self.attributes.get("id", ""),
            "className": self.attributes.get("class", ""),
            "ariaLabel": self.name or self.attributes.get("aria-label", ""),
            "title": self.attributes.get("title", ""),
            "name": self.attributes.get("name", ""),
            "href": self.attributes.get("href", ""),
            "selector": self.selector,
            "position": self.bounds,
            "role": self.role,
            "node_id": self.node_id,
            "is_interactive": self.is_interactive,
            "shadow_root": self.shadow_root,
        }


class CDPDomProcessor:
    """
    Extracts interactive elements from a page using Chrome DevTools Protocol.
    
    Combines two data sources:
    1. Accessibility Tree — semantic understanding of elements
    2. DOMSnapshot — full layout with computed styles and bounds
    
    Provides a unified element list compatible with IntelligentElementFinder.
    """
    
    # Roles considered interactive in accessibility tree
    INTERACTIVE_ROLES = frozenset({
        "button", "link", "textbox", "searchbox", "combobox",
        "checkbox", "radio", "switch", "slider", "spinbutton",
        "tab", "menuitem", "menuitemcheckbox", "menuitemradio",
        "option", "treeitem", "gridcell", "columnheader", "rowheader",
    })
    
    # Tags considered natively interactive
    INTERACTIVE_TAGS = frozenset({
        "a", "button", "input", "textarea", "select", "option",
        "details", "summary", "label",
    })
    
    @staticmethod
    async def is_cdp_available(page: Page) -> bool:
        """Check if CDP is available (Chromium-based browser)."""
        try:
            client = await page.context.new_cdp_session(page)
            await client.detach()
            return True
        except Exception:
            return False
    
    @staticmethod
    async def get_accessibility_elements(page: Page) -> List[CDPElement]:
        """
        Extract interactive elements from the accessibility tree.
        
        Uses Playwright's built-in accessibility.snapshot() which is
        available across browsers and provides semantic element data.
        """
        elements = []
        
        try:
            snapshot = await page.accessibility.snapshot(interesting_only=False)
            if not snapshot:
                logger.warning("Accessibility snapshot returned empty")
                return elements
            
            # Flatten the tree
            _flatten_ax_tree(snapshot, elements, index_counter=[0])
            
        except Exception as e:
            logger.warning(f"Accessibility tree extraction failed: {e}")
        
        return elements
    
    @staticmethod
    async def get_dom_snapshot_elements(page: Page) -> List[CDPElement]:
        """
        Extract elements using CDP DOMSnapshot.captureSnapshot.
        
        Provides computed styles, bounding boxes, and paint order.
        Only works on Chromium-based browsers.
        """
        elements = []
        
        try:
            client = await page.context.new_cdp_session(page)
            
            try:
                # Capture full DOM snapshot with layout info
                snapshot = await client.send("DOMSnapshot.captureSnapshot", {
                    "computedStyles": [
                        "display", "visibility", "opacity", 
                        "pointer-events", "cursor", "position"
                    ],
                    "includeDOMRects": True,
                    "includePaintOrder": True,
                })
                
                elements = _parse_dom_snapshot(snapshot)
                
            finally:
                await client.detach()
                
        except Exception as e:
            logger.warning(f"DOMSnapshot extraction failed: {e}")
        
        return elements
    
    @staticmethod
    async def get_interactive_elements(page: Page) -> List[CDPElement]:
        """
        Get all interactive elements using the best available method.
        
        Strategy:
        1. Get accessibility tree (always available, semantic)
        2. Try CDP DOMSnapshot (Chromium only, provides bounds + styles)
        3. Merge results, deduplicating by position/selector
        4. Filter to interactive elements only
        
        Returns:
            List of CDPElement objects, ready for AI matching
        """
        # Get accessibility elements (always available)
        ax_elements = await CDPDomProcessor.get_accessibility_elements(page)
        logger.info(f"Accessibility tree: {len(ax_elements)} elements")
        
        # Try CDP DOMSnapshot (Chromium only)
        dom_elements = []
        try:
            dom_elements = await CDPDomProcessor.get_dom_snapshot_elements(page)
            logger.info(f"DOMSnapshot: {len(dom_elements)} elements")
        except Exception:
            logger.debug("DOMSnapshot unavailable, using accessibility tree only")
        
        # Merge: enrich AX elements with DOM bounds/styles
        merged = _merge_elements(ax_elements, dom_elements)
        
        # Filter to interactive only
        interactive = [e for e in merged if e.is_interactive]
        
        # Assign sequential indices
        for i, elem in enumerate(interactive):
            elem.index = i
        
        logger.info(f"CDP discovery: {len(interactive)} interactive elements (from {len(merged)} total)")
        return interactive
    
    @staticmethod
    async def get_element_by_node_id(page: Page, node_id: int) -> Optional[Dict]:
        """Resolve a CDP node to Playwright-usable element info."""
        try:
            client = await page.context.new_cdp_session(page)
            try:
                result = await client.send("DOM.describeNode", {
                    "backendNodeId": node_id
                })
                return result.get("node", {})
            finally:
                await client.detach()
        except Exception as e:
            logger.debug(f"Could not resolve node {node_id}: {e}")
            return None


def _flatten_ax_tree(
    node: Dict[str, Any], 
    elements: List[CDPElement], 
    index_counter: List[int],
    depth: int = 0,
    max_depth: int = 15
) -> None:
    """
    Recursively flatten accessibility tree into CDPElement list.
    
    Filters to interactive elements and elements with text content.
    """
    if depth > max_depth:
        return
    
    role = node.get("role", "").lower()
    name = node.get("name", "").strip()
    value = str(node.get("value", "")).strip() if node.get("value") else ""
    
    # Determine interactivity
    is_interactive = (
        role in CDPDomProcessor.INTERACTIVE_ROLES
        or node.get("focused", False)
        or node.get("haspopup") is not None
    )
    
    # Include if interactive or has meaningful content
    if is_interactive or (name and role not in ("none", "presentation", "generic", "")):
        elem = CDPElement(
            role=role,
            name=name,
            text=name,  # AX tree 'name' is typically the accessible text
            value=value,
            is_interactive=is_interactive,
            is_focused=node.get("focused", False),
            is_disabled=node.get("disabled", False),
            is_visible=True,  # AX tree only includes visible nodes by default
            index=index_counter[0],
        )
        
        # Infer tag from role
        role_to_tag = {
            "button": "button",
            "link": "a",
            "textbox": "input",
            "searchbox": "input",
            "combobox": "select",
            "checkbox": "input",
            "radio": "input",
            "switch": "input",
            "slider": "input",
            "spinbutton": "input",
            "tab": "div",
            "heading": "h2",
            "img": "img",
        }
        elem.tag_name = role_to_tag.get(role, "div")
        
        # Generate a basic selector from role + name
        if name and len(name) < 50:
            safe_name = name.replace('"', '\\"')
            if role in ("button", "link"):
                elem.selector = f'{role}:has-text("{safe_name[:30]}")'
            elif role in ("textbox", "searchbox"):
                elem.selector = f'input[aria-label="{safe_name}"], input[placeholder="{safe_name}"]'
            else:
                elem.selector = f'[role="{role}"]'
        else:
            elem.selector = f'[role="{role}"]'
        
        elements.append(elem)
        index_counter[0] += 1
    
    # Recurse into children
    for child in node.get("children", []):
        _flatten_ax_tree(child, elements, index_counter, depth + 1, max_depth)


def _parse_dom_snapshot(snapshot: Dict[str, Any]) -> List[CDPElement]:
    """
    Parse CDP DOMSnapshot.captureSnapshot response into CDPElement list.
    
    The snapshot format has parallel arrays for documents, with each document
    containing arrays of node data indexed by position.
    """
    elements = []
    
    documents = snapshot.get("documents", [])
    strings = snapshot.get("strings", [])
    
    def get_string(idx: int) -> str:
        """Resolve string table index."""
        if 0 <= idx < len(strings):
            return strings[idx]
        return ""
    
    for doc_idx, doc in enumerate(documents):
        nodes = doc.get("nodes", {})
        layout = doc.get("layout", {})
        
        node_names = nodes.get("nodeName", [])
        node_types = nodes.get("nodeType", [])
        node_values = nodes.get("nodeValue", [])
        attributes_arr = nodes.get("attributes", [])
        backend_node_ids = nodes.get("backendNodeId", [])
        parent_indices = nodes.get("parentIndex", [])
        is_clickable = nodes.get("isClickable", {})
        
        # Layout info
        layout_node_indices = layout.get("nodeIndex", [])
        layout_bounds = layout.get("bounds", [])
        layout_styles = layout.get("styles", [])
        
        # Build layout lookup
        bounds_map = {}
        styles_map = {}
        for i, node_idx in enumerate(layout_node_indices):
            if i < len(layout_bounds):
                bounds_map[node_idx] = layout_bounds[i]
            if i < len(layout_styles):
                styles_map[node_idx] = layout_styles[i]
        
        # Process element nodes (nodeType 1)
        for i in range(len(node_names)):
            if i >= len(node_types):
                break
                
            node_type = node_types[i]
            if node_type != 1:  # Only element nodes
                continue
            
            tag_name = get_string(node_names[i]).lower()
            
            # Parse attributes
            attrs = {}
            if i < len(attributes_arr):
                attr_list = attributes_arr[i]
                for j in range(0, len(attr_list) - 1, 2):
                    attr_name = get_string(attr_list[j])
                    attr_value = get_string(attr_list[j + 1])
                    if attr_name:
                        attrs[attr_name] = attr_value
            
            # Get bounds
            bounds = {}
            if i in bounds_map:
                b = bounds_map[i]
                if len(b) >= 4:
                    bounds = {"x": b[0], "y": b[1], "width": b[2], "height": b[3]}
            
            # Determine visibility from computed styles
            is_visible = True
            if i in styles_map:
                style_indices = styles_map[i]
                # computedStyles requested: display, visibility, opacity, pointer-events, cursor, position
                if len(style_indices) >= 3:
                    display = get_string(style_indices[0]) if style_indices[0] >= 0 else ""
                    visibility = get_string(style_indices[1]) if style_indices[1] >= 0 else ""
                    opacity = get_string(style_indices[2]) if style_indices[2] >= 0 else ""
                    
                    if display == "none" or visibility == "hidden":
                        is_visible = False
                    try:
                        if opacity and float(opacity) < 0.1:
                            is_visible = False
                    except (ValueError, TypeError):
                        pass
            
            # Also not visible if zero-size bounds
            if bounds and bounds.get("width", 0) <= 0 and bounds.get("height", 0) <= 0:
                is_visible = False
            
            if not is_visible:
                continue
            
            # Determine interactivity
            is_interactive = (
                tag_name in CDPDomProcessor.INTERACTIVE_TAGS
                or attrs.get("role") in CDPDomProcessor.INTERACTIVE_ROLES
                or "onclick" in attrs
                or attrs.get("tabindex", "") not in ("", "-1")
                or any(cls in attrs.get("class", "").lower() 
                       for cls in ("btn", "button", "clickable", "link"))
            )
            
            backend_id = backend_node_ids[i] if i < len(backend_node_ids) else 0
            
            # Generate selector
            selector = _generate_selector(tag_name, attrs)
            
            elem = CDPElement(
                node_id=backend_id,
                tag_name=tag_name,
                role=attrs.get("role", ""),
                name=attrs.get("aria-label", attrs.get("title", "")),
                text=attrs.get("aria-label", attrs.get("title", attrs.get("alt", ""))),
                value=attrs.get("value", ""),
                attributes=attrs,
                bounds=bounds,
                is_visible=is_visible,
                is_interactive=is_interactive,
                selector=selector,
            )
            
            elements.append(elem)
    
    return elements


def _generate_selector(tag_name: str, attrs: Dict[str, str]) -> str:
    """Generate the best CSS selector for an element from its attributes."""
    # Priority: id > name > aria-label > data-testid > type+placeholder > role > tag
    if attrs.get("id"):
        return f"#{attrs['id']}"
    if attrs.get("name"):
        return f'{tag_name}[name="{attrs["name"]}"]'
    if attrs.get("aria-label"):
        return f'[aria-label="{attrs["aria-label"]}"]'
    if attrs.get("data-testid"):
        return f'[data-testid="{attrs["data-testid"]}"]'
    if tag_name == "input" and attrs.get("type"):
        if attrs.get("placeholder"):
            return f'input[type="{attrs["type"]}"][placeholder="{attrs["placeholder"]}"]'
        return f'input[type="{attrs["type"]}"]'
    if attrs.get("role"):
        return f'[role="{attrs["role"]}"]'
    return tag_name


def _merge_elements(
    ax_elements: List[CDPElement], 
    dom_elements: List[CDPElement]
) -> List[CDPElement]:
    """
    Merge accessibility tree elements with DOMSnapshot elements.
    
    Strategy:
    - AX elements provide semantic data (role, accessible name)
    - DOM elements provide geometry (bounds) and computed styles
    - Match by selector similarity and enrich AX elements with DOM data
    - Add DOM-only interactive elements not in AX tree
    """
    if not dom_elements:
        return ax_elements
    
    if not ax_elements:
        return dom_elements
    
    # Build lookup of DOM elements by selector for fast matching
    dom_by_selector: Dict[str, CDPElement] = {}
    for elem in dom_elements:
        if elem.selector:
            dom_by_selector[elem.selector] = elem
    
    # Enrich AX elements with DOM data
    matched_dom_selectors = set()
    for ax_elem in ax_elements:
        if ax_elem.selector in dom_by_selector:
            dom_elem = dom_by_selector[ax_elem.selector]
            # Enrich with geometry and node ID
            if dom_elem.bounds:
                ax_elem.bounds = dom_elem.bounds
            if dom_elem.node_id and not ax_elem.node_id:
                ax_elem.node_id = dom_elem.node_id
            if dom_elem.attributes:
                # Merge attributes (AX takes priority for conflicts)
                merged_attrs = {**dom_elem.attributes}
                merged_attrs.update(ax_elem.attributes)
                ax_elem.attributes = merged_attrs
            matched_dom_selectors.add(ax_elem.selector)
    
    # Add DOM-only interactive elements not in AX tree
    merged = list(ax_elements)
    for elem in dom_elements:
        if elem.selector not in matched_dom_selectors and elem.is_interactive:
            merged.append(elem)
    
    return merged
