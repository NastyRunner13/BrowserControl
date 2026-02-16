"""
Tests for CDP-Level DOM Processing.

Tests element extraction, accessibility tree parsing, DOMSnapshot parsing,
visibility filtering, selector generation, and element merging.
"""

import pytest
from core.cdp_dom import (
    CDPElement,
    CDPDomProcessor,
    _flatten_ax_tree,
    _parse_dom_snapshot,
    _generate_selector,
    _merge_elements,
)


class TestCDPElement:
    """Test CDPElement dataclass."""

    def test_default_creation(self):
        elem = CDPElement()
        assert elem.tag_name == ""
        assert elem.role == ""
        assert elem.is_visible is True
        assert elem.is_interactive is False
        assert elem.bounds == {}

    def test_creation_with_values(self):
        elem = CDPElement(
            node_id=42,
            tag_name="button",
            role="button",
            name="Submit",
            text="Submit Form",
            is_interactive=True,
            bounds={"x": 100, "y": 200, "width": 80, "height": 30},
        )
        assert elem.node_id == 42
        assert elem.tag_name == "button"
        assert elem.role == "button"
        assert elem.name == "Submit"
        assert elem.is_interactive is True

    def test_to_dict_format(self):
        elem = CDPElement(
            tag_name="input",
            role="textbox",
            name="Search",
            text="Search",
            value="hello",
            attributes={"type": "text", "placeholder": "Type here", "id": "search-input"},
            bounds={"x": 10, "y": 20, "width": 200, "height": 30},
            selector='#search-input',
            is_interactive=True,
        )
        d = elem.to_dict()

        assert d["tagName"] == "input"
        assert d["role"] == "textbox"
        assert d["ariaLabel"] == "Search"
        assert d["type"] == "text"
        assert d["placeholder"] == "Type here"
        assert d["id"] == "search-input"
        assert d["selector"] == "#search-input"
        assert d["position"]["x"] == 10
        assert d["is_interactive"] is True

    def test_to_dict_defaults(self):
        elem = CDPElement(tag_name="div")
        d = elem.to_dict()
        assert d["tagName"] == "div"
        assert d["type"] == ""
        assert d["placeholder"] == ""
        assert d["id"] == ""
        assert d["ariaLabel"] == ""


class TestFlattenAxTree:
    """Test accessibility tree flattening."""

    def test_simple_tree(self):
        tree = {
            "role": "WebArea",
            "name": "",
            "children": [
                {"role": "button", "name": "Click Me"},
                {"role": "link", "name": "Go Home", "children": []},
                {"role": "textbox", "name": "Search"},
            ]
        }
        elements = []
        _flatten_ax_tree(tree, elements, [0])
        
        interactive = [e for e in elements if e.is_interactive]
        assert len(interactive) == 3
        assert interactive[0].role == "button"
        assert interactive[0].name == "Click Me"
        assert interactive[1].role == "link"
        assert interactive[2].role == "textbox"

    def test_nested_tree(self):
        tree = {
            "role": "WebArea",
            "name": "",
            "children": [
                {
                    "role": "navigation",
                    "name": "Nav",
                    "children": [
                        {"role": "link", "name": "Home"},
                        {"role": "link", "name": "About"},
                    ]
                }
            ]
        }
        elements = []
        _flatten_ax_tree(tree, elements, [0])
        
        links = [e for e in elements if e.role == "link"]
        assert len(links) == 2

    def test_max_depth_limit(self):
        # Build deeply nested tree
        node = {"role": "generic", "name": "deep", "children": []}
        current = node
        for i in range(20):
            child = {"role": "button", "name": f"btn{i}", "children": []}
            current["children"] = [child]
            current = child
        
        elements = []
        _flatten_ax_tree(node, elements, [0], max_depth=5)
        
        # Should stop before reaching all buttons
        buttons = [e for e in elements if e.role == "button"]
        assert len(buttons) < 20

    def test_filters_generic_no_name(self):
        tree = {
            "role": "generic",
            "name": "",
            "children": [
                {"role": "generic", "name": ""},
                {"role": "button", "name": "OK"},
            ]
        }
        elements = []
        _flatten_ax_tree(tree, elements, [0])
        
        # Generic with no name should be filtered
        generics = [e for e in elements if e.role == "generic" and not e.name]
        assert len(generics) == 0

    def test_tag_inference(self):
        tree = {
            "role": "button",
            "name": "Submit"
        }
        elements = []
        _flatten_ax_tree(tree, elements, [0])
        assert elements[0].tag_name == "button"

    def test_textbox_tag_inference(self):
        tree = {"role": "textbox", "name": "Email"}
        elements = []
        _flatten_ax_tree(tree, elements, [0])
        assert elements[0].tag_name == "input"

    def test_selector_generation_for_button(self):
        tree = {"role": "button", "name": "Login"}
        elements = []
        _flatten_ax_tree(tree, elements, [0])
        assert "Login" in elements[0].selector

    def test_selector_generation_for_textbox(self):
        tree = {"role": "textbox", "name": "Password"}
        elements = []
        _flatten_ax_tree(tree, elements, [0])
        assert "Password" in elements[0].selector


class TestParseDomSnapshot:
    """Test DOMSnapshot parsing."""

    def _make_snapshot(self, nodes_data, layout_data=None):
        """Helper to create a minimal DOMSnapshot response."""
        strings = []
        string_map = {}

        def add_string(s):
            if s not in string_map:
                string_map[s] = len(strings)
                strings.append(s)
            return string_map[s]

        node_names = []
        node_types = []
        node_values = []
        attributes = []
        backend_ids = []

        for i, node in enumerate(nodes_data):
            node_names.append(add_string(node.get("name", "")))
            node_types.append(node.get("type", 1))
            node_values.append(add_string(node.get("value", "")))
            
            attrs = node.get("attrs", {})
            attr_list = []
            for k, v in attrs.items():
                attr_list.append(add_string(k))
                attr_list.append(add_string(v))
            attributes.append(attr_list)
            backend_ids.append(node.get("backend_id", i + 1))

        layout = layout_data or {"nodeIndex": [], "bounds": [], "styles": []}

        return {
            "documents": [{
                "nodes": {
                    "nodeName": node_names,
                    "nodeType": node_types,
                    "nodeValue": node_values,
                    "attributes": attributes,
                    "backendNodeId": backend_ids,
                    "parentIndex": [],
                },
                "layout": layout,
            }],
            "strings": strings,
        }

    def test_parses_button_element(self):
        snapshot = self._make_snapshot([
            {"name": "BUTTON", "type": 1, "attrs": {"role": "button", "aria-label": "Submit"}}
        ])
        elements = _parse_dom_snapshot(snapshot)
        assert len(elements) >= 1
        buttons = [e for e in elements if e.tag_name == "button"]
        assert len(buttons) == 1
        assert buttons[0].is_interactive is True

    def test_parses_input_element(self):
        snapshot = self._make_snapshot([
            {"name": "INPUT", "type": 1, "attrs": {"type": "text", "placeholder": "Search..."}}
        ])
        elements = _parse_dom_snapshot(snapshot)
        inputs = [e for e in elements if e.tag_name == "input"]
        assert len(inputs) == 1
        assert inputs[0].is_interactive is True

    def test_skips_text_nodes(self):
        snapshot = self._make_snapshot([
            {"name": "#text", "type": 3, "value": "Hello"},
        ])
        elements = _parse_dom_snapshot(snapshot)
        assert len(elements) == 0

    def test_skips_hidden_elements(self):
        """Elements with display:none should be filtered."""
        # String table: 0="DIV", 1="none", 2=""
        strings = ["DIV", "none", ""]
        snapshot = {
            "documents": [{
                "nodes": {
                    "nodeName": [0],  # DIV
                    "nodeType": [1],
                    "nodeValue": [2],  # empty
                    "attributes": [[]],
                    "backendNodeId": [1],
                    "parentIndex": [],
                },
                "layout": {
                    "nodeIndex": [0],
                    "bounds": [[0, 0, 100, 50]],
                    "styles": [[1, 2, 2]],  # display="none", visibility="", opacity=""
                },
            }],
            "strings": strings,
        }
        elements = _parse_dom_snapshot(snapshot)
        assert len(elements) == 0

    def test_empty_snapshot(self):
        snapshot = {"documents": [], "strings": []}
        elements = _parse_dom_snapshot(snapshot)
        assert elements == []


class TestGenerateSelector:
    """Test CSS selector generation."""

    def test_id_selector(self):
        assert _generate_selector("div", {"id": "main"}) == "#main"

    def test_name_selector(self):
        assert _generate_selector("input", {"name": "email"}) == 'input[name="email"]'

    def test_aria_label_selector(self):
        assert _generate_selector("button", {"aria-label": "Close"}) == '[aria-label="Close"]'

    def test_data_testid_selector(self):
        assert _generate_selector("div", {"data-testid": "header"}) == '[data-testid="header"]'

    def test_input_type_placeholder(self):
        result = _generate_selector("input", {"type": "text", "placeholder": "Search"})
        assert 'type="text"' in result
        assert 'placeholder="Search"' in result

    def test_input_type_only(self):
        result = _generate_selector("input", {"type": "password"})
        assert result == 'input[type="password"]'

    def test_role_selector(self):
        assert _generate_selector("div", {"role": "navigation"}) == '[role="navigation"]'

    def test_fallback_tag(self):
        assert _generate_selector("span", {}) == "span"

    def test_priority_id_over_name(self):
        result = _generate_selector("input", {"id": "email", "name": "email"})
        assert result == "#email"


class TestMergeElements:
    """Test element merging logic."""

    def test_merge_empty_dom(self):
        ax = [CDPElement(role="button", name="OK", selector='[role="button"]')]
        result = _merge_elements(ax, [])
        assert len(result) == 1
        assert result[0].role == "button"

    def test_merge_empty_ax(self):
        dom = [CDPElement(tag_name="button", is_interactive=True, selector="#btn")]
        result = _merge_elements([], dom)
        assert len(result) == 1

    def test_enriches_ax_with_dom_bounds(self):
        ax = [CDPElement(role="button", name="OK", selector="#ok")]
        dom = [CDPElement(
            tag_name="button",
            selector="#ok",
            node_id=42,
            bounds={"x": 10, "y": 20, "width": 80, "height": 30},
        )]
        result = _merge_elements(ax, dom)
        assert len(result) == 1
        assert result[0].bounds == {"x": 10, "y": 20, "width": 80, "height": 30}
        assert result[0].node_id == 42

    def test_adds_dom_only_interactive(self):
        ax = [CDPElement(role="button", name="OK", selector="#ok")]
        dom = [
            CDPElement(tag_name="button", selector="#ok"),
            CDPElement(tag_name="a", selector="#link", is_interactive=True),
        ]
        result = _merge_elements(ax, dom)
        assert len(result) == 2  # Original + new interactive

    def test_does_not_add_dom_non_interactive(self):
        ax = [CDPElement(role="button", name="OK", selector="#ok")]
        dom = [
            CDPElement(tag_name="div", selector="#wrapper", is_interactive=False),
        ]
        result = _merge_elements(ax, dom)
        assert len(result) == 1  # Only the AX element


class TestCDPDomProcessorConstants:
    """Test CDPDomProcessor constants and configuration."""

    def test_interactive_roles(self):
        assert "button" in CDPDomProcessor.INTERACTIVE_ROLES
        assert "link" in CDPDomProcessor.INTERACTIVE_ROLES
        assert "textbox" in CDPDomProcessor.INTERACTIVE_ROLES
        assert "checkbox" in CDPDomProcessor.INTERACTIVE_ROLES

    def test_interactive_tags(self):
        assert "a" in CDPDomProcessor.INTERACTIVE_TAGS
        assert "button" in CDPDomProcessor.INTERACTIVE_TAGS
        assert "input" in CDPDomProcessor.INTERACTIVE_TAGS
        assert "select" in CDPDomProcessor.INTERACTIVE_TAGS
