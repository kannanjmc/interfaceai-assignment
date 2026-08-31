"""
Surface abstraction layer.

This module defines the interface for interacting with different application surfaces
(web, desktop, legacy web, etc.). The key design principle is that the artifact
schema and replay logic should be surface-agnostic - they operate on a unified
abstraction of "observe state" and "perform action" regardless of the underlying
technology.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class SurfaceType(str, Enum):
    """Types of application surfaces."""
    WEB = "web"
    LEGACY_WEB = "legacy_web"
    DESKTOP = "desktop"
    MOBILE = "mobile"


@dataclass
class ElementState:
    """State of a UI element."""
    visible: bool
    enabled: bool
    text: Optional[str] = None
    attributes: Dict[str, Any] = None
    position: Optional[Dict[str, int]] = None  # x, y coordinates
    role: Optional[str] = None  # ARIA role or accessibility role


@dataclass
class PageState:
    """Snapshot of the current application state."""
    url: Optional[str] = None
    title: Optional[str] = None
    elements: List[Dict[str, Any]] = None
    screenshot_path: Optional[str] = None
    accessibility_tree: Optional[Dict[str, Any]] = None
    raw_dom: Optional[str] = None


class SurfaceInterface(ABC):
    """
    Abstract interface for interacting with application surfaces.
    
    This abstraction allows the same artifact/replay logic to work across
    different surface types (web, desktop, legacy web) by providing a unified
    set of operations for observing state and performing actions.
    """
    
    @abstractmethod
    async def connect(self, target: str) -> None:
        """Connect to the target application surface."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the surface and clean up resources."""
        pass
    
    @abstractmethod
    async def get_state(self) -> PageState:
        """
        Get the current state of the application.
        
        Returns a structured snapshot that an LLM can reason about and
        that can be used for checkpoint verification and evidence collection.
        """
        pass
    
    @abstractmethod
    async def find_element(self, locator: Dict[str, Any]) -> Optional[ElementState]:
        """
        Find an element using the provided locator strategy.
        
        Supports multiple locator types with fallbacks:
        - css_selector, xpath, text, role_and_text, aria_label, test_id, accessibility_id
        """
        pass
    
    @abstractmethod
    async def click(self, locator: Dict[str, Any]) -> bool:
        """Click on an element identified by the locator."""
        pass
    
    @abstractmethod
    async def type_text(self, locator: Dict[str, Any], text: str) -> bool:
        """Type text into an element identified by the locator."""
        pass
    
    @abstractmethod
    async def navigate(self, url: str) -> bool:
        """Navigate to the specified URL."""
        pass
    
    @abstractmethod
    async def wait_for(self, condition: Dict[str, Any], timeout_ms: int = 30000) -> bool:
        """
        Wait for a condition to be met.
        
        Conditions can include:
        - element_visible: wait for element to be visible
        - element_hidden: wait for element to be hidden
        - text_present: wait for text to appear
        - url_contains: wait for URL to contain substring
        """
        pass
    
    @abstractmethod
    async def extract_text(self, locator: Dict[str, Any]) -> Optional[str]:
        """Extract text content from an element."""
        pass
    
    @abstractmethod
    async def take_screenshot(self, path: str) -> str:
        """Take a screenshot and save to the specified path."""
        pass
    
    @abstractmethod
    async def get_accessibility_tree(self) -> Dict[str, Any]:
        """
        Get the accessibility tree representation.
        
        This is often more stable than raw DOM for legacy applications
        and is the primary interface for desktop applications.
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the surface is currently connected."""
        pass
    
    @abstractmethod
    async def pause_automation(self) -> None:
        """
        Pause automation and prepare for human control.
        
        This is the key seam for human-in-the-loop: the automation stops
        but the session remains live for a human to take over.
        """
        pass
    
    @abstractmethod
    async def resume_automation(self) -> None:
        """
        Resume automation after human handoff.
        
        The automation continues from the current state of the live session.
        """
        pass


class WebSurface(SurfaceInterface):
    """
    Web application surface using Playwright.
    
    This implementation handles both modern web apps and legacy web apps
    (tables, framesets, non-semantic markup) by prioritizing accessibility
    tree and text-based locators over fragile DOM selectors.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self._connected = False
    
    async def connect(self, target: str) -> None:
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Computer-Use-Automation/1.0'
        )
        self.page = await self.context.new_page()
        
        if target:
            await self.page.goto(target, wait_until="networkidle")
        
        self._connected = True
    
    async def disconnect(self) -> None:
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        self._connected = False
    
    async def get_state(self) -> PageState:
        if not self._connected:
            raise RuntimeError("Surface not connected")
        
        # Get basic page info
        url = self.page.url
        title = await self.page.title()
        
        # Get accessibility tree (more stable than DOM for legacy apps)
        accessibility_tree = await self.get_accessibility_tree()
        
        # Get screenshot for evidence
        screenshot_path = None
        # Screenshot would be saved to evidence directory
        
        return PageState(
            url=url,
            title=title,
            accessibility_tree=accessibility_tree,
            screenshot_path=screenshot_path
        )
    
    async def find_element(self, locator: Dict[str, Any]) -> Optional[ElementState]:
        """Find element using locator with fallback strategies."""
        if not self._connected:
            raise RuntimeError("Surface not connected")
        
        # Try primary locator
        element = await self._try_locator(locator)
        if element:
            return await self._get_element_state(element)
        
        # Try fallbacks if specified
        fallbacks = locator.get("fallbacks", [])
        for fallback in fallbacks:
            element = await self._try_locator(fallback)
            if element:
                return await self._get_element_state(element)
        
        return None
    
    async def _try_locator(self, locator: Dict[str, Any]):
        """Try a single locator strategy."""
        locator_type = locator.get("type")
        value = locator.get("value")
        
        try:
            if locator_type == "css_selector":
                return await self.page.query_selector(value)
            elif locator_type == "xpath":
                return await self.page.query_selector(f"xpath={value}")
            elif locator_type == "text":
                return await self.page.get_by_text(value).first
            elif locator_type == "role_and_text":
                role = locator.get("role")
                text = locator.get("text")
                return await self.page.get_by_role(role, name=text).first
            elif locator_type == "aria_label":
                return await self.page.get_by_label(value).first
            elif locator_type == "test_id":
                return await self.page.get_by_test_id(value).first
            elif locator_type == "accessibility_id":
                # For web, map to aria-label or data-testid
                return await self.page.get_by_label(value).first
        except Exception:
            return None
        
        return None
    
    async def _get_element_state(self, element) -> ElementState:
        """Extract state information from an element."""
        is_visible = await element.is_visible()
        is_enabled = await element.is_enabled()
        text_content = await element.text_content()
        
        # Get bounding box for position
        box = None
        try:
            box = await element.bounding_box()
        except Exception:
            pass
        
        return ElementState(
            visible=is_visible,
            enabled=is_enabled,
            text=text_content,
            position={"x": box["x"], "y": box["y"]} if box else None
        )
    
    async def click(self, locator: Dict[str, Any]) -> bool:
        element = await self.find_element(locator)
        if element and element.visible:
            await element.click()
            return True
        return False
    
    async def type_text(self, locator: Dict[str, Any], text: str) -> bool:
        element = await self.find_element(locator)
        if element and element.visible:
            await element.fill(text)
            return True
        return False
    
    async def navigate(self, url: str) -> bool:
        await self.page.goto(url, wait_until="networkidle")
        return True
    
    async def wait_for(self, condition: Dict[str, Any], timeout_ms: int = 30000) -> bool:
        condition_type = condition.get("type")
        value = condition.get("value")
        
        try:
            if condition_type == "element_visible":
                await self.page.wait_for_selector(value, timeout=timeout_ms)
                return True
            elif condition_type == "text_present":
                await self.page.wait_for_function(f"() => document.body.innerText.includes('{value}')", timeout=timeout_ms)
                return True
            elif condition_type == "url_contains":
                await self.page.wait_for_url(f"**{value}*", timeout=timeout_ms)
                return True
        except Exception:
            return False
        
        return False
    
    async def extract_text(self, locator: Dict[str, Any]) -> Optional[str]:
        element = await self.find_element(locator)
        if element:
            return element.text
        return None
    
    async def take_screenshot(self, path: str) -> str:
        await self.page.screenshot(path=path)
        return path
    
    async def get_accessibility_tree(self) -> Dict[str, Any]:
        """Get the accessibility tree as a structured representation."""
        # Playwright exposes accessibility tree through the context
        from playwright.async_api import async_playwright
        # For now, return a simple representation since accessibility API varies
        # In production, this would use the proper accessibility snapshot
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "content": await self.page.content()
        }
    
    def is_connected(self) -> bool:
        return self._connected
    
    async def pause_automation(self) -> None:
        """
        Pause automation for human handoff.
        
        For web, this means keeping the browser session alive but stopping
        automated actions. The human can interact with the same browser instance.
        """
        # In a real implementation, this might:
        # - Keep the browser open
        # - Expose the CDP (Chrome DevTools Protocol) endpoint for remote control
        # - Signal to an operator console that the session is available
        pass
    
    async def resume_automation(self) -> None:
        """
        Resume automation after human handoff.
        
        The automation continues from the current state of the browser.
        """
        # Re-attach to the page and continue execution
        pass


class LegacyWebSurface(WebSurface):
    """
    Legacy web application surface.
    
    Extends WebSurface with strategies for dealing with:
    - Framesets and iframes
    - Table-based layouts
    - Non-semantic markup
    - Dynamic or missing IDs
    - No test IDs
    
    Key difference: prioritizes text-based and accessibility-based locators
    over CSS selectors that are likely to be fragile.
    """
    
    async def find_element(self, locator: Dict[str, Any]) -> Optional[ElementState]:
        """
        Find element with legacy-friendly strategies.
        
        For legacy apps, we:
        1. Prefer text-based locators (visible text is usually stable)
        2. Use accessibility tree (more stable than DOM)
        3. Fall back to structural DOM only when necessary
        4. Handle frames/iframes transparently
        """
        # Try text-based locators first (most stable in legacy apps)
        if "text" in locator:
            text_locator = {"type": "text", "value": locator["text"]}
            element = await self._try_locator(text_locator)
            if element:
                return await self._get_element_state(element)
        
        # Try accessibility-based locators
        if "aria_label" in locator or "role" in locator:
            element = await self._try_locator(locator)
            if element:
                return await self._get_element_state(element)
        
        # Fall back to DOM-based locators
        return await super().find_element(locator)


class DesktopSurface(SurfaceInterface):
    """
    Desktop application surface (placeholder for future implementation).
    
    Would use OS-level automation frameworks like:
    - Windows: UI Automation, WinAppDriver
    - Mac: Accessibility API
    - Linux: AT-SPI / LDTP
    
    The key is that the artifact schema doesn't need to change - we just
    implement the SurfaceInterface for desktop using the appropriate OS APIs.
    """
    
    async def connect(self, target: str) -> None:
        """Connect to desktop application (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def disconnect(self) -> None:
        """Disconnect from desktop application (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def get_state(self) -> PageState:
        """Get desktop app state (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def find_element(self, locator: Dict[str, Any]) -> Optional[ElementState]:
        """Find element in desktop app (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def click(self, locator: Dict[str, Any]) -> bool:
        """Click in desktop app (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def type_text(self, locator: Dict[str, Any], text: str) -> bool:
        """Type in desktop app (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def navigate(self, url: str) -> bool:
        """Navigate not applicable to desktop (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def wait_for(self, condition: Dict[str, Any], timeout_ms: int = 30000) -> bool:
        """Wait in desktop app (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def extract_text(self, locator: Dict[str, Any]) -> Optional[str]:
        """Extract text from desktop app (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def take_screenshot(self, path: str) -> str:
        """Screenshot of desktop app (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def get_accessibility_tree(self) -> Dict[str, Any]:
        """Get accessibility tree from desktop OS (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    def is_connected(self) -> bool:
        """Check if connected to desktop app (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def pause_automation(self) -> None:
        """Pause desktop automation (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")
    
    async def resume_automation(self) -> None:
        """Resume desktop automation (placeholder)."""
        raise NotImplementedError("Desktop surface not yet implemented")


def create_surface(surface_type: SurfaceType, **kwargs) -> SurfaceInterface:
    """
    Factory function to create the appropriate surface implementation.
    
    This is the seam where we can extend to new surface types without
    changing the artifact schema or replay logic.
    """
    if surface_type == SurfaceType.WEB:
        return WebSurface(**kwargs)
    elif surface_type == SurfaceType.LEGACY_WEB:
        return LegacyWebSurface(**kwargs)
    elif surface_type == SurfaceType.DESKTOP:
        return DesktopSurface(**kwargs)
    else:
        raise ValueError(f"Unsupported surface type: {surface_type}")
