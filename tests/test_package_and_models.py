import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT/'plugins/pair-watch'


class PackageTest(unittest.TestCase):
    def test_invalid_package_variants_are_rejected(self):
        spec = importlib.util.spec_from_file_location('validator',ROOT/'scripts/validate-package.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        module.validate(ROOT)
        for failure in ('missing','version','outside','bad-type'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)/'repo'; root.mkdir()
                for name in ('.claude-plugin','.agents','plugins'):
                    shutil.copytree(ROOT/name,root/name)
                manifest = root/'plugins/pair-watch/.codex-plugin/plugin.json'
                if failure == 'missing': manifest.unlink()
                elif failure == 'version':
                    data=json.loads(manifest.read_text()); data['version']='99.0.0'; manifest.write_text(json.dumps(data))
                elif failure == 'bad-type': manifest.write_text('[]')
                else:
                    p=root/'.agents/plugins/marketplace.json';data=json.loads(p.read_text());data['plugins'][0]['source']['path']='./../';p.write_text(json.dumps(data))
                with self.assertRaises((OSError,ValueError)):module.validate(root)

    def test_model_settings_override_missing_cli_and_runtime_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); bin=root/'bin';bin.mkdir()
            for name in ('codex','claude'):
                p=bin/name;p.write_text('#!/bin/sh\nexit 99\n');p.chmod(0o755)
            candidates=['codex:fixture-one(high)','claude:fixture-two(low)']
            (root/'pair-watch.settings.json').write_text(json.dumps({'reviewer':candidates}))
            script=PLUGIN/'skills/pair-watch/scripts/resolve-model.py'
            env={**os.environ,'PATH':str(bin)}
            argv=[sys.executable,str(script),'--repo',str(root),'--primary','codex','--role','reviewer']
            def call(*extra):return subprocess.run(argv+list(extra),env=env,capture_output=True,text=True)
            self.assertEqual(json.loads(call().stdout)['candidate'],candidates[0])
            default_role=subprocess.run([sys.executable,str(script),'--repo',str(root),'--primary','codex','--role','implementer'],env=env,capture_output=True,text=True)
            self.assertTrue(json.loads(default_role.stdout)['source'].endswith('references/model-defaults.json'))
            self.assertEqual(json.loads(call('--unavailable',candidates[0]+'=rate-limit').stdout)['candidate'],candidates[1])
            self.assertEqual(call('--unavailable',candidates[0]+'=test-failure').returncode,2)
            (bin/'codex').unlink()
            self.assertEqual(json.loads(call().stdout)['candidate'],candidates[1])
            (bin/'claude').unlink()
            self.assertEqual(call().returncode,1)

    def test_actual_hook_command_for_both_plugin_roots(self):
        command=json.loads((PLUGIN/'hooks/hooks.json').read_text())['hooks']['SessionStart'][0]['hooks'][0]['command']
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);market=root/'market';cached=root/'cache/pair-watch/pair-watch/0.4.0'
            shutil.copytree(PLUGIN,cached)
            for name in ('.agents','.claude-plugin','plugins'):
                shutil.copytree(ROOT/name,market/name)
            other=root/'other';shutil.copytree(market,other)
            for kind in ('claude','codex'):
                p=other/f'plugins/pair-watch/.{kind}-plugin/plugin.json';d=json.loads(p.read_text());d['version']='99.0.0';p.write_text(json.dumps(d))
            bin=root/'bin';bin.mkdir()
            binary=bin/'codex';binary.write_text('#!/bin/sh\ncat <<\'JSON\'\n'+json.dumps({'marketplaces':[{'name':'unrelated','root':str(root/'other')},{'name':'pair-watch','root':str(market)}]})+'\nJSON\n');binary.chmod(0o755)
            home=root/'home';(home/'.claude/plugins').mkdir(parents=True)
            (home/'.claude/plugins/known_marketplaces.json').write_text(json.dumps({'unrelated':{'installLocation':str(root/'other')},'pair-watch':{'installLocation':str(market)}}))
            for provider,var in [('claude','CLAUDE_PLUGIN_ROOT'),('codex','PLUGIN_ROOT')]:
                env={k:v for k,v in os.environ.items() if k not in ('PLUGIN_ROOT','CLAUDE_PLUGIN_ROOT')}
                env.update({var:str(cached),'HOME':str(home),'PATH':str(bin)+os.pathsep+os.environ['PATH']})
                p=cached/f'.{provider}-plugin/plugin.json';original=json.loads(p.read_text())
                for version,warn in [('0.4.0',True),('0.5.0',False),('9.0.0',False)]:
                    p.write_text(json.dumps({**original,'version':version}))
                    result=subprocess.run(['bash','-c',command],env=env,capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(bool(result.stdout.strip()),warn,(provider,version,result.stdout,result.stderr))
                    if warn:self.assertIn(provider+' plugin',result.stdout)


if __name__ == '__main__': unittest.main()
