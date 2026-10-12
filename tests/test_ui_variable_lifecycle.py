"""Real Tcl observer ownership: destroyed screens must be collectable."""

import gc
import tkinter as tk
import unittest
import weakref

from ui import trace_owned


class ObserverOwner(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.variable = tk.StringVar(parent)
        self.changes = 0
        self.trace_id = trace_owned(self, self.variable, self.changed)

    def changed(self, *args):
        self.changes += 1


class VariableLifecycleTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"Tk display unavailable: {error}")
        self.root.withdraw()

    def tearDown(self):
        if hasattr(self, "root"):
            self.root.destroy()

    def test_destroy_releases_tcl_callback_and_python_owner(self):
        baseline = set(self.root.tk.call("info", "vars", "PY_VAR*"))
        for _ in range(16):
            owner = ObserverOwner(self.root)
            owner.pack()
            self.root.update()
            variable = owner.variable
            owner_ref, variable_ref = weakref.ref(owner), weakref.ref(variable)
            variable.set("busca")
            self.assertEqual(owner.changes, 1)
            trace_id = owner.trace_id
            # Descendant destruction must not remove its parent's observer.
            child = tk.Label(owner, text="Filho")
            child.destroy()
            variable.set("outra busca")
            self.assertEqual(owner.changes, 2)
            owner.destroy()
            self.assertEqual(variable.trace_info(), [])
            self.assertFalse(self.root.tk.call("info", "commands", trace_id))
            del owner, variable, child
            gc.collect()
            self.assertIsNone(owner_ref())
            self.assertIsNone(variable_ref())
        self.assertEqual(set(self.root.tk.call("info", "vars", "PY_VAR*")), baseline)
