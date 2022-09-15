#  ___________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright (c) 2008-2022
#  National Technology and Engineering Solutions of Sandia, LLC
#  Under the terms of Contract DE-NA0003525 with National Technology and
#  Engineering Solutions of Sandia, LLC, the U.S. Government retains certain
#  rights in this software.
#  This software is distributed under the 3-clause BSD License.
#  ___________________________________________________________________________

import pyomo.common.unittest as unittest
from pyomo.contrib.cp import IntervalVar, Step, Pulse
from pyomo.contrib.cp.scheduling_expr.step_function_expressions import (
    AlwaysIn, CumulativeFunction, NegatedStepFunction)

from pyomo.environ import ConcreteModel, LogicalConstraint

class CommonTests(unittest.TestCase):
    def get_model(self):
        m = ConcreteModel()
        m.a = IntervalVar()
        m.b = IntervalVar()
        m.c = IntervalVar([1,2])

        return m

class TestPulse(CommonTests):
    def test_bad_interval_var(self):
        with self.assertRaisesRegex(
                TypeError,
                "The 'interval_var' argument for a 'Pulse' must "
                "be an 'IntervalVar'.\n"
                "Received: <class 'float'>"):
            thing = Pulse(1.2, height=4)

    def test_create_pulse_with_scalar_interval_var(self):
        m = self.get_model()
        p = Pulse(m.a, 1)

        self.assertIsInstance(p, Pulse)
        self.assertEqual(str(p), "Pulse(a, height=1)")

    def test_create_pulse_with_interval_var_data(self):
        m = self.get_model()
        p = Pulse(m.c[2], 2)
        self.assertIsInstance(p, Pulse)
        self.assertEqual(str(p), "Pulse(c[2], height=2)")

class TestStep(CommonTests):
    def test_bad_time_point(self):
        m = self.get_model()
        with self.assertRaisesRegex(
                TypeError,
                "The 'time' argument for a 'Step' must be either "
                "an 'IntervalVarTimePoint' \(for example, the "
                "'start_time' or 'end_time' of an IntervalVar\) or "
                "an integer time point in the time horizon.\n"
                "Received: "
                "<class 'pyomo.contrib.cp.interval_var.ScalarIntervalVar'>"):
            thing = Step(m.a, height=2)

class TestSumStepFunctions(CommonTests):
    def test_sum_step_and_pulse(self):
        m = self.get_model()
        expr = Step(m.a.start_time, height=4) + Pulse(m.b, height=-1)

        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(len(expr.args), 2)
        self.assertEqual(expr.nargs(), 2)
        self.assertIsInstance(expr.args[0], Step)
        self.assertIsInstance(expr.args[1], Pulse)

        self.assertEqual(str(expr), "Step(a.start_time, height=4) + "
                         "Pulse(b, height=-1)")

    def test_args_clone_correctly(self):
        m = self.get_model()
        expr = Step(m.a.start_time, height=4) + Pulse(m.b, height=-1)
        expr2 = expr + Step(m.b.end_time, height=4)

        self.assertIsInstance(expr2, CumulativeFunction)
        self.assertEqual(len(expr2.args), 3)
        self.assertEqual(expr2.nargs(), 3)
        self.assertIsInstance(expr2.args[0], Step)
        self.assertIsInstance(expr2.args[1], Pulse)
        self.assertIsInstance(expr2.args[2], Step)

        # This will force expr to clone its arguments because it did the
        # appending trick to make expr2.
        expr3 = expr + Pulse(m.b, height=-5)

        self.assertIsInstance(expr3, CumulativeFunction)
        self.assertEqual(len(expr3.args), 3)
        self.assertEqual(expr3.nargs(), 3)
        self.assertIsInstance(expr3.args[0], Step)
        self.assertIsInstance(expr3.args[1], Pulse)
        self.assertIsInstance(expr3.args[2], Pulse)

    def test_args_clone_correctly_in_place(self):
        m = self.get_model()
        s1 = Step(m.a.start_time, height=1)
        s2 = Step(m.b.end_time, height=1)
        s3 = Step(m.b.start_time, height=2)
        p = Pulse(m.b, height=3)

        e1 = s1 + s2
        e2 = e1 + s3
        e3 = e1
        e3 += p

        self.assertIsInstance(e1, CumulativeFunction)
        self.assertEqual(e1.nargs(), 2)
        self.assertIs(e1.args[0], s1)
        self.assertIs(e1.args[1], s2)

        self.assertIsInstance(e2, CumulativeFunction)
        self.assertEqual(e2.nargs(), 3)
        self.assertIs(e2.args[0], s1)
        self.assertIs(e2.args[1], s2)
        self.assertIs(e2.args[2], s3)

        self.assertIsInstance(e3, CumulativeFunction)
        self.assertEqual(e3.nargs(), 3)
        self.assertIs(e3.args[0], s1)
        self.assertIs(e3.args[1], s2)
        self.assertIs(e3.args[2], p)

    def test_sum_two_pulses(self):
        m = self.get_model()
        m.p1 = Pulse(m.a, height=3)
        m.p2 = Pulse(m.b, height=-2)

        expr = m.p1 + m.p2

        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(len(expr.args), 2)
        self.assertEqual(expr.nargs(), 2)
        self.assertIs(expr.args[0], m.p1)
        self.assertIs(expr.args[1], m.p2)

    def test_sum_in_place(self):
        m = self.get_model()
        expr = Step(m.a.start_time, height=4) + Pulse(m.b, height=-1)
        expr += Step(0, 1)

        self.assertEqual(len(expr.args), 3)
        self.assertEqual(expr.nargs(), 3)
        self.assertIsInstance(expr.args[0], Step)
        self.assertIsInstance(expr.args[1], Pulse)
        self.assertIsInstance(expr.args[2], Step)

        self.assertEqual(str(expr), "Step(a.start_time, height=4) + "
                         "Pulse(b, height=-1) + Step(0, height=1)")

    def test_sum_steps_in_place(self):
        m = self.get_model()
        s1 = Step(m.a.end_time, height=2)
        expr = s1

        self.assertIsInstance(expr, Step)
        self.assertEqual(len(expr.args), 1)
        self.assertEqual(expr.nargs(), 1)

        s2 = Step(m.b.end_time, height=3)
        expr += s2

        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(len(expr.args), 2)
        self.assertEqual(expr.nargs(), 2)
        self.assertIs(expr.args[0], s1)
        self.assertIs(expr.args[1], s2)

    def test_sum_pulses_in_place(self):
        m = self.get_model()
        p1 = Pulse(m.a, height=2)
        expr = p1

        self.assertIsInstance(expr, Pulse)
        self.assertEqual(len(expr.args), 1)
        self.assertEqual(expr.nargs(), 1)

        p2 = Pulse(m.b, height=3)
        expr += p2

        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(len(expr.args), 2)
        self.assertEqual(expr.nargs(), 2)
        self.assertIs(expr.args[0], p1)
        self.assertIs(expr.args[1], p2)

    def test_cannot_add_constant(self):
        m = self.get_model()
        with self.assertRaisesRegex(
                TypeError,
                "Cannot add object of class <class 'int'> to object of class "
                "<class 'pyomo.contrib.cp.scheduling_expr."
                "step_function_expressions.Step'>"):
            expr = Step(m.a.start_time, height=6) + 3

    def test_cannot_add_to_constant(self):
        m = self.get_model()
        with self.assertRaisesRegex(
                TypeError,
                "Cannot add object of class <class 'pyomo.contrib.cp."
                "scheduling_expr.step_function_expressions.Step'> to object "
                "of class <class 'int'>"):
            expr = 4 + Step(m.a.start_time, height=6)

    def test_python_sum_funct(self):
        # We allow adding to 0 so that sum() works as expected
        m = self.get_model()
        expr = sum(Pulse(m.c[i], height=1) for i in [1,2])

        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(len(expr.args), 2)
        self.assertEqual(expr.nargs(), 2)
        self.assertIsInstance(expr.args[0], Pulse)
        self.assertIsInstance(expr.args[1], Pulse)

class TestSubtractStepFunctions(CommonTests):
    def test_subtract_two_steps(self):
        m = self.get_model()

        s = Step(m.a.start_time, height=2) - Step(m.b.start_time, height=5)

        self.assertIsInstance(s, CumulativeFunction)
        self.assertEqual(len(s.args), 2)
        self.assertEqual(s.nargs(), 2)
        self.assertIsInstance(s.args[0], Step)
        self.assertIsInstance(s.args[1], NegatedStepFunction)
        self.assertEqual(len(s.args[1].args), 1)
        self.assertEqual(s.args[1].nargs(), 1)
        self.assertIsInstance(s.args[1].args[0], Step)

    def test_subtract_step_and_pulse(self):
        m = self.get_model()
        s1 = Step(m.a.end_time, height=2)
        s2 = Step(m.b.start_time, height=5)
        p = Pulse(m.a, height=3)

        expr = s1 - s2 - p

        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(len(expr.args), 3)
        self.assertEqual(expr.nargs(), 3)
        self.assertIs(expr.args[0], s1)
        self.assertIsInstance(expr.args[1], NegatedStepFunction)
        self.assertIs(expr.args[1].args[0], s2)
        self.assertIsInstance(expr.args[2], NegatedStepFunction)
        self.assertIs(expr.args[2].args[0], p)

    def test_subtract_pulse_from_two_steps(self):
        m = self.get_model()
        s1 = Step(m.a.end_time, height=2)
        s2 = Step(m.b.start_time, height=5)
        p = Pulse(m.a, height=3)

        expr = s1 + s2 - p
        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(len(expr.args), 3)
        self.assertEqual(expr.nargs(), 3)
        self.assertIs(expr.args[0], s1)
        self.assertIs(expr.args[1], s2)
        self.assertIsInstance(expr.args[2], NegatedStepFunction)
        self.assertIs(expr.args[2].args[0], p)

    def test_args_clone_correctly(self):
        m = self.get_model()
        m.p1 = Pulse(m.a, height=3)
        m.p2 = Pulse(m.b, height=4)
        m.s = Step(m.a.start_time, height=-1)

        expr1 = m.p1 - m.p2
        self.assertIsInstance(expr1, CumulativeFunction)
        self.assertEqual(expr1.nargs(), 2)
        self.assertIs(expr1.args[0], m.p1)
        self.assertIsInstance(expr1.args[1], NegatedStepFunction)
        self.assertIs(expr1.args[1].args[0], m.p2)

        expr2 = m.p1 - m.s
        self.assertIsInstance(expr2, CumulativeFunction)
        self.assertEqual(expr2.nargs(), 2)
        self.assertIs(expr2.args[0], m.p1)
        self.assertIsInstance(expr2.args[1], NegatedStepFunction)
        self.assertIs(expr2.args[1].args[0], m.s)

    def test_args_clone_correctly_in_place(self):
        m = self.get_model()
        m.p1 = Pulse(m.a, height=3)
        m.p2 = Pulse(m.b, height=4)
        m.s = Step(m.a.start_time, height=-1)

        expr1 = m.p1 - m.p2
        # This will append p1 to expr1's args
        expr = expr1 + m.p1
        # Now we have to clone in place
        expr1 -= m.s

        self.assertIsInstance(expr1, CumulativeFunction)
        self.assertEqual(expr1.nargs(), 3)
        self.assertIs(expr1.args[0], m.p1)
        self.assertIsInstance(expr1.args[1], NegatedStepFunction)
        self.assertIs(expr1.args[1].args[0], m.p2)
        self.assertIsInstance(expr1.args[2], NegatedStepFunction)
        self.assertIs(expr1.args[2].args[0], m.s)

        # and expr is what we expect too
        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(expr.nargs(), 3)
        self.assertIs(expr.args[0], m.p1)
        self.assertIsInstance(expr.args[1], NegatedStepFunction)
        self.assertIs(expr.args[1].args[0], m.p2)
        self.assertIs(expr.args[2], m.p1)

    def test_subtract_pulses_in_place(self):
        m = self.get_model()
        p1 = Pulse(m.a, height = 1)
        p2 = Pulse(m.b, height = 3)

        expr = p1
        expr -= p2

        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(len(expr.args), 2)
        self.assertEqual(expr.nargs(), 2)
        self.assertIs(expr.args[0], p1)
        self.assertIsInstance(expr.args[1], NegatedStepFunction)
        self.assertIs(expr.args[1].args[0], p2)

    def test_subtract_steps_in_place(self):
        m = self.get_model()
        s1 = Step(m.a.start_time, height = 1)
        s2 = Step(m.b.end_time, height = 3)

        expr = s1
        expr -= s2

        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(len(expr.args), 2)
        self.assertEqual(expr.nargs(), 2)
        self.assertIs(expr.args[0], s1)
        self.assertIsInstance(expr.args[1], NegatedStepFunction)
        self.assertIs(expr.args[1].args[0], s2)

    def test_subtract_from_cumul_func_in_place(self):
        m = self.get_model()
        m.p1 = Pulse(m.a, height=5)
        m.p2 = Pulse(m.b, height=-3)
        m.s = Step(m.b.end_time, height=5)

        expr = m.p1 + m.s
        expr -= m.p2

        self.assertIsInstance(expr, CumulativeFunction)
        self.assertEqual(expr.nargs(), 3)
        self.assertIs(expr.args[0], m.p1)
        self.assertIs(expr.args[1], m.s)
        self.assertIsInstance(expr.args[2], NegatedStepFunction)
        self.assertIs(expr.args[2].args[0], m.p2)

        self.assertEqual(str(expr), "Pulse(a, height=5) + "
                         "Step(b.end_time, height=5) - Pulse(b, height=-3)")

    def test_cannot_subtract_constant(self):
        m = self.get_model()
        with self.assertRaisesRegex(
                TypeError,
                "Cannot subtract object of class <class 'int'> from object of "
                "class <class 'pyomo.contrib.cp."
                "scheduling_expr.step_function_expressions.Step'>"):
            expr = Step(m.a.start_time, height=6) - 3

    def test_cannot_subtract_from_constant(self):
        m = self.get_model()
        with self.assertRaisesRegex(
                TypeError,
                "Cannot subtract object of class <class 'pyomo.contrib.cp."
                "scheduling_expr.step_function_expressions.Step'> from object "
                "of class <class 'int'>"):
            expr = 3 - Step(m.a.start_time, height=6)

class TestAlwaysIn(CommonTests):
    def test_always_in(self):
        m = self.get_model()
        f = Pulse(m.a, height=3) + Step(m.b.start_time, height=2) - \
            Step(m.a.end_time, height=-1)

        m.c = LogicalConstraint(expr=f.within((0, 3), (0, 10)))
        self.assertIsInstance(m.c.expr, AlwaysIn)

        self.assertEqual(m.c.expr.nargs(), 3)
        self.assertEqual(len(m.c.expr.args), 3)
        self.assertIs(m.c.expr.args[0], f)
        self.assertEqual(m.c.expr.args[1], (0, 3))
        self.assertEqual(m.c.expr.args[2], (0, 10))

        self.assertEqual(
            str(m.c.expr),
            "(Pulse(a, height=3) + Step(b.start_time, height=2) - "
            "Step(a.end_time, height=-1)).within(bounds=(0, 3), "
            "times=(0, 10))")
