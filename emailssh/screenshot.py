"""Screen capture; tries mss then Pillow, returns PNG bytes or error string."""

from __future__ import annotations

import io


def capture() -> tuple[bytes, str]:
    """Returns (png_bytes, error_msg). On success error_msg is empty."""
    try:
        import mss
        import mss.tools

        with mss.mss() as sct:
            monitor = sct.monitors[0]
            img = sct.grab(monitor)
            png_bytes = mss.tools.to_png(img.rgb, img.size)
        return png_bytes, ""
    except ImportError:
        pass
    except Exception as exc:
        return b"", f"mss capture failed: {exc}"

    try:
        from PIL import ImageGrab

        img = ImageGrab.grab(all_screens=True)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), ""
    except ImportError:
        pass
    except Exception as exc:
        return b"", f"Pillow capture failed: {exc}"

    return b"", "Screenshot unavailable: install 'mss' (pip install mss) or 'Pillow'"
