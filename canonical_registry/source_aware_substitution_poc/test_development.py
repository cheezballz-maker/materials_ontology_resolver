import concurrent.futures,base64,json,os,subprocess,unittest,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B/'nomenclature_semantic_integration'))
from graph_correspondence import correspond

class DevelopmentTraceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.rows={x['name']:x for x in json.loads((H/'development_observations.json').read_text(encoding='utf8'))}
 def test_three_independent_substitution_traces(self):
  for n in ('1-methyl-1H-pyrazole','1-ethyl-1H-pyrazole','1-methyl-1H-imidazole'):
   with self.subTest(name=n):
    x=self.rows[n];e=x['events'][0];self.assertEqual(x['status'],'SUCCESS');self.assertTrue(x['single_selected_parse']);self.assertTrue(e['locant_span_verified']);self.assertTrue(e['group_span_verified']);self.assertEqual(e['substituent_span_status'],'OBSERVED_CONTIGUOUS_PARSER_TOKENS');self.assertTrue(e['same_h_atom']);self.assertTrue(e['parent_before_substitution']);self.assertTrue(e['graph_bond_verified']);self.assertFalse(e['clone_activity']);self.assertIn(x['candidate_correspondence']['status'],('MAPPED','AMBIGUOUS'));self.assertEqual(x['operation_state'],'UNKNOWN')
 def test_different_attachment_is_not_guessed_as_semantic_contradiction(self):
  a=self.rows['1-methyl-1H-pyrazole'];b=self.rows['3-methyl-1H-pyrazole'];self.assertFalse(b['events'][0]['same_h_atom']);self.assertEqual(correspond(a['cml'],b['resolver_snapshot_candidate']['smiles'])['status'],'UNKNOWN');self.assertEqual(a['operation_state'],'UNKNOWN')
 def test_warning_unicode_and_clone_do_not_promote(self):
  for n in ('methyl-1H-pyrazole','1-methyl-1H-pyrazole - water (2:1)','1-methyl−1H-pyrazole'):
   self.assertEqual(self.rows[n]['operation_state'],'UNKNOWN')
  self.assertEqual(self.rows['methyl-1H-pyrazole']['status'],'WARNING')
  self.assertTrue(self.rows['1-methyl-1H-pyrazole - water (2:1)']['events'][0]['clone_activity'])
  self.assertEqual(self.rows['1-methyl−1H-pyrazole']['events'][0]['source_provenance'],'UNKNOWN')
 def test_public_outputs_preserved(self):self.assertTrue(all(x['public_equal'] for x in self.rows.values()))
 def test_process_isolation(self):
  root=Path(json.loads((H/'build.json').read_text())['temp_build']);cp=os.pathsep.join(map(str,[root/'substitution-classes',root/'source/opsin-core/src/main/resources',root/'opsin-core-2.9.0.jar']))
  names=['1-methyl-1H-pyrazole','methyl-1H-pyrazole','1-ethyl-1H-pyrazole']
  def run(n):
   enc=base64.b64encode(n.encode()).decode();p=subprocess.run(['java','-Dprobe.trace=true','-cp',cp,'uk.ac.cam.ch.wwmm.opsin.Runner',enc],capture_output=True,text=True,encoding='utf8',check=True,timeout=20)
   rows=[x.split('\t') for x in p.stdout.splitlines() if x.startswith('R\t')];return base64.b64decode(rows[0][1]).decode()
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:self.assertEqual(list(pool.map(run,names)),names)

if __name__=='__main__':unittest.main()
