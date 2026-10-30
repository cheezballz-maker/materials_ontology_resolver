import unittest
from architecture_A.implementation.interpreter import interpret_name,validate_candidate
class AdapterTests(unittest.TestCase):
 def test_fail_closed_even_with_trace(self):
  x=interpret_name('1-methyl-1H-pyrazole');self.assertIn(x.scope_status,('IN_CONTRACT','UNKNOWN'));self.assertEqual(validate_candidate(x,'CN1C=CC=N1').result,'UNKNOWN')
 def test_scope(self):self.assertEqual(interpret_name('methyl-1H-pyrazole').scope_status,'OUT_OF_CONTRACT')
if __name__=='__main__':unittest.main()
