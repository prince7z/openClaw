"""Semantic visible DOM crawler and PageState generator (Asynchronous)."""

import logging
from typing import Any
from app.tools.browser.schemas import BrowserElement, PageState
from app.tools.browser.state import state_manager

logger = logging.getLogger("openclaw-agent")


async def extract_page_state(session: str = "default") -> PageState:
    """Extract a highly compact, semantic PageState from Playwright page DOM contents.

    Uses a client-side JS evaluation query to scan for visible buttons, inputs, links,
    notifications, catalog products, and errors, generating stable locator patterns.

    Args:
        session: Named browser session.

    Returns:
        PageState model.
    """
    s = await state_manager.get_session(session)
    url = s.page.url
    title = await s.page.title()

    dom_script = """
    () => {
        const res = {
            inputs: [],
            buttons: [],
            links: [],
            products: [],
            errors: [],
            notifications: [],
            scroll_position: { x: window.scrollX, y: window.scrollY }
        };

        const isVisible = (el) => {
            if (!el) return false;
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return false;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) return false;
            return true;
        };

        const getElementText = (el) => {
            let txt = "";
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                txt = el.placeholder || el.getAttribute('aria-label') || el.getAttribute('name') || el.value || "";
            } else {
                txt = el.innerText || el.getAttribute('aria-label') || "";
            }
            return txt.trim().replace(/\\s+/g, ' ');
        };

        const getLocator = (el, role) => {
            if (el.getAttribute('data-testid')) {
                return `css=[data-testid="${el.getAttribute('data-testid')}"]`;
            }
            if (el.id && !el.id.includes('__') && isNaN(el.id.slice(-3))) {
                return `css=#${el.id}`;
            }

            const text = getElementText(el);
            const escaped = text.replace(/"/g, '\\"');

            if (role === 'button') {
                return text ? `role=button[name="${escaped}"]` : `role=button`;
            }
            if (role === 'link') {
                return text ? `role=link[name="${escaped}"]` : `role=link`;
            }
            if (role === 'input') {
                const ph = el.placeholder || el.getAttribute('placeholder');
                if (ph) return `css=[placeholder="${ph.replace(/"/g, '\\"')}"]`;
                const name = el.getAttribute('name');
                if (name) return `css=[name="${name.replace(/"/g, '\\"')}"]`;
                const al = el.getAttribute('aria-label');
                if (al) return `css=[aria-label="${al.replace(/"/g, '\\"')}"]`;
                return `role=textbox`;
            }

            return text ? `text="${escaped}"` : "";
        };

        const all = document.getElementsByTagName('*');
        const seen = new Set();

        for (let i = 0; i < all.length; i++) {
            const el = all[i];
            if (!isVisible(el)) continue;

            const tag = el.tagName;
            const role = el.getAttribute('role');
            const type = el.getAttribute('type');

            if (tag === 'BUTTON' || (tag === 'INPUT' && (type === 'submit' || type === 'button' || type === 'reset')) || role === 'button') {
                const label = getElementText(el);
                const locator = getLocator(el, 'button');
                if (locator && !seen.has(locator)) {
                    seen.add(locator);
                    res.buttons.push({ text: label || "Button", role: 'button', locator });
                }
            }
            else if (tag === 'TEXTAREA' || tag === 'SELECT' || (tag === 'INPUT' && type !== 'hidden' && type !== 'submit' && type !== 'button' && type !== 'reset') || role === 'textbox' || el.getAttribute('contenteditable') === 'true') {
                const label = getElementText(el);
                const locator = getLocator(el, 'input');
                if (locator && !seen.has(locator)) {
                    seen.add(locator);
                    res.inputs.push({ text: label || el.value || "", role: tag === 'SELECT' ? 'combobox' : 'textbox', locator });
                }
            }
            else if (tag === 'A' || role === 'link') {
                const label = getElementText(el);
                const href = el.getAttribute('href');
                if (!label && !href) continue;

                const locator = getLocator(el, 'link');
                if (locator && !seen.has(locator)) {
                    seen.add(locator);
                    res.links.push({ text: label || href || "Link", role: 'link', locator });
                }
            }
        }

        // Scan errors
        document.querySelectorAll('.error, .error-message, [role="alert"], .invalid-feedback').forEach(el => {
            if (isVisible(el)) {
                const txt = el.innerText.trim();
                if (txt && !res.errors.includes(txt)) res.errors.push(txt);
            }
        });

        // Scan notifications
        document.querySelectorAll('.toast, .notification, .banner, .alert-success').forEach(el => {
            if (isVisible(el)) {
                const txt = el.innerText.trim();
                if (txt && !res.notifications.includes(txt)) res.notifications.push(txt);
            }
        });

        // Scan catalog products
        const priceRegex = /[₹$]\\s?\\d+(?:\\.\\d+)?/;
        const seenProds = new Set();
        document.querySelectorAll('div, li, section').forEach(el => {
            if (isVisible(el) && el.offsetWidth > 100 && el.offsetHeight > 100 && el.children.length > 1) {
                const text = el.innerText;
                const match = priceRegex.exec(text);
                if (match) {
                    const price = match[0];
                    const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                    if (lines.length >= 2) {
                        const name = lines[0];
                        if (name.length < 60 && !seenProds.has(name) && isNaN(name)) {
                            seenProds.add(name);
                            const btn = el.querySelector('button, [role="button"]');
                            let locator = "";
                            if (btn && btn.innerText.trim()) {
                                locator = `role=button[name="${btn.innerText.trim().replace(/"/g, '\\"')}"]`;
                            }
                            res.products.push({
                                name,
                                price,
                                locator: locator || `text="${name.replace(/"/g, '\\"')}"`
                            });
                        }
                    }
                }
            }
        });

        return res;
    }
    """
    dom_data = {}
    try:
        dom_data = await s.page.evaluate(dom_script)
    except Exception as exc:
        logger.warning(f"Semantic DOM extraction failed: {exc}")

    # Build Pydantic lists mapping visual IDs
    inputs = []
    inp_cnt = 0
    for inp in dom_data.get("inputs") or []:
        inp_cnt += 1
        clean_lbl = "".join(c if c.isalnum() else "_" for c in inp["text"].lower()).strip("_")
        clean_lbl = "_".join(filter(None, clean_lbl.split("_")))
        element_id = f"inp_{clean_lbl}" if clean_lbl else f"inp_{inp_cnt}"
        inputs.append(
            BrowserElement(
                id=element_id,
                text=inp["text"],
                role=inp["role"],
                locator=inp["locator"]
            )
        )

    buttons = []
    btn_cnt = 0
    for btn in dom_data.get("buttons") or []:
        btn_cnt += 1
        clean_lbl = "".join(c if c.isalnum() else "_" for c in btn["text"].lower()).strip("_")
        clean_lbl = "_".join(filter(None, clean_lbl.split("_")))
        element_id = f"btn_{clean_lbl}" if clean_lbl else f"btn_{btn_cnt}"
        buttons.append(
            BrowserElement(
                id=element_id,
                text=btn["text"],
                role=btn["role"],
                locator=btn["locator"]
            )
        )

    links = []
    lnk_cnt = 0
    for lnk in dom_data.get("links") or []:
        lnk_cnt += 1
        clean_lbl = "".join(c if c.isalnum() else "_" for c in lnk["text"].lower()).strip("_")
        clean_lbl = "_".join(filter(None, clean_lbl.split("_")))
        element_id = f"lnk_{clean_lbl}" if clean_lbl else f"lnk_{lnk_cnt}"
        links.append(
            BrowserElement(
                id=element_id,
                text=lnk["text"],
                role=lnk["role"],
                locator=lnk["locator"]
            )
        )

    products = []
    prod_cnt = 0
    for prod in dom_data.get("products") or []:
        prod_cnt += 1
        clean_lbl = "".join(c if c.isalnum() else "_" for c in prod["name"].lower()).strip("_")
        clean_lbl = "_".join(filter(None, clean_lbl.split("_")))
        element_id = f"prod_{clean_lbl}" if clean_lbl else f"prod_{prod_cnt}"
        products.append(
            BrowserElement(
                id=element_id,
                text=f"{prod['name']} ({prod['price']})",
                role="product",
                locator=prod["locator"]
            )
        )

    dialogs = list(s.dialogs)
    errors = dom_data.get("errors") or []
    notifications = dom_data.get("notifications") or []

    # Map semantic action hints
    actions = []
    if inputs:
        actions.append("Search")
    if any("login" in e.id for e in buttons):
        actions.append("Login")
    if products:
        actions.append("Add to Cart")
    if any("cart" in e.id or "checkout" in e.id for e in buttons):
        actions.append("Checkout")

    # Prune summary description
    summary = f"Loaded page '{title}' at {url}."
    if inputs:
        summary += f" Displays {len(inputs)} input fields."
    if buttons:
        summary += f" Contains {len(buttons)} actionable buttons."
    if products:
        summary += f" Renders {len(products)} products catalog items."
    if dialogs:
        summary += f" Has active dialog alert: '{dialogs[-1]}'."

    return PageState(
        url=url,
        title=title,
        inputs=inputs,
        buttons=buttons,
        links=links,
        products=products,
        dialogs=dialogs,
        notifications=notifications,
        errors=errors,
        scroll_position=dom_data.get("scroll_position") or {"x": 0, "y": 0},
        actions=actions,
        page_summary=summary
    )
