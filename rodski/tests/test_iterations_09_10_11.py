"""Acceptance tests for iterations 09, 10, 11"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import MagicMock, patch
from core.runtime_context import RuntimeContext
from core.exceptions import DriverError, InvalidParameterError


def make_engine():
    from core.keyword_engine import KeywordEngine
    eng = KeywordEngine.__new__(KeywordEngine)
    eng._context = RuntimeContext()
    eng.driver = MagicMock()
    eng.model_parser = None
    eng.data_manager = None
    eng.data_resolver = None
    eng._variables = {}
    eng._SELECTOR_PREFIXES = ("#", ".", "//", "css=", "xpath=", "id=", "text=")
    return eng


class TestIteration09_RuntimeContext(unittest.TestCase):

    def test_fields_exist(self):
        ctx = RuntimeContext()
        self.assertIsInstance(ctx.history, list)
        self.assertIsInstance(ctx.named, dict)
        self.assertIsInstance(ctx.objects, dict)

    def test_append_and_get_history(self):
        ctx = RuntimeContext()
        ctx.append_history("a")
        ctx.append_history("b")
        ctx.append_history("c")
        self.assertEqual(ctx.get_history(-1), "c")
        self.assertEqual(ctx.get_history(-2), "b")

    def test_get_history_out_of_bounds(self):
        ctx = RuntimeContext()
        self.assertIsNone(ctx.get_history(-1))
        ctx.append_history("x")
        self.assertIsNone(ctx.get_history(-99))

    def test_engine_store_get_return(self):
        eng = make_engine()
        eng.store_return("val1")
        eng.store_return("val2")
        self.assertEqual(eng.get_return(-1), "val2")
        self.assertEqual(eng.get_return(-2), "val1")


class TestIteration10_Evaluate(unittest.TestCase):

    def test_evaluate_raises_for_non_playwright(self):
        eng = make_engine()
        eng.driver = MagicMock()  # not a PlaywrightDriver
        with self.assertRaises(DriverError) as cm:
            eng._kw_evaluate({"data": "1+1"})
        self.assertIn("仅支持 Web 浏览器驱动", str(cm.exception))

    def test_evaluate_no_str_conversion(self):
        """store_return should receive raw result, not str(result)"""
        from drivers.playwright_driver import PlaywrightDriver
        eng = make_engine()
        mock_driver = MagicMock(spec=PlaywrightDriver)
        mock_driver.page = MagicMock()
        mock_driver.page.evaluate.return_value = 42
        eng.driver = mock_driver
        eng._kw_evaluate({"data": "21*2"})
        self.assertEqual(eng.get_return(-1), 42)  # int, not "42"


class TestIteration11_GetSet(unittest.TestCase):

    def test_set_writes_named_and_history(self):
        eng = make_engine()
        eng._kw_set({"data": "mykey=hello"})
        self.assertEqual(eng._context.named["mykey"], "hello")
        self.assertEqual(eng.get_return(-1), "hello")

    def test_get_named_mode(self):
        eng = make_engine()
        eng._context.named["mykey"] = "world"
        eng._kw_get({"data": "mykey"})
        self.assertEqual(eng.get_return(-1), "world")

    def test_get_undefined_key_raises(self):
        eng = make_engine()
        with self.assertRaises(InvalidParameterError) as cm:
            eng._kw_get({"data": "undefined_key"})
        self.assertIn("undefined_key", str(cm.exception))

    def test_get_selector_mode(self):
        eng = make_engine()
        eng.driver.get_text_locator = MagicMock(return_value="some text")
        eng._kw_get({"data": "#my-selector"})
        eng.driver.get_text_locator.assert_called_once_with("#my-selector")
        self.assertEqual(eng.get_return(-1), "some text")

    def test_get_text_deprecated_delegates(self):
        import warnings
        eng = make_engine()
        eng._context.named["k"] = "v"
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            eng._kw_get_text({"data": "k"})
        self.assertTrue(any("get_text 已废弃" in str(x.message) for x in w))
        self.assertEqual(eng.get_return(-1), "v")


if __name__ == "__main__":
    unittest.main(verbosity=2)
