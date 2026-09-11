"""Resize the user-approved icon; do not redraw it or change site content."""
from pathlib import Path
from PIL import Image
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'assets/approved-icon-192.webp'
assert hashlib.sha256(source.read_bytes()).hexdigest() == 'd35c63deb75c80879d6537699e01239841a7ab3387a3fb4e8f519cdd5aceb2b1'
image = Image.open(source).convert('RGBA')
assert image.size == (192, 192)
outputs = {'favicon-96x96.png': 96, 'apple-touch-icon.png': 180}
for name, size in outputs.items():
    image.resize((size, size), Image.Resampling.LANCZOS).save(ROOT/name, 'PNG', optimize=True)
image.save(ROOT/'favicon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48)])
with Image.open(ROOT/'favicon.ico') as ico:
    assert ico.ico.sizes() == {(16,16),(32,32),(48,48)}
for name, size in outputs.items():
    with Image.open(ROOT/name) as check:
        assert check.size == (size, size)

block = '''\n<!-- Approved Open Close Map site icons -->
<link rel="icon" href="/favicon.ico" type="image/x-icon" sizes="16x16 32x32 48x48">
<link rel="icon" href="/favicon-96x96.png" type="image/png" sizes="96x96">
<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">
'''
changed = []
paths = subprocess.check_output(['git','ls-files','-z','--','*.html'], cwd=ROOT).decode().split('\0')
for name in filter(None, paths):
    path = ROOT/name
    old = path.read_text()
    if '<!-- Approved Open Close Map site icons -->' in old:
        continue
    if '</head>' not in old.lower():
        continue  # Google verification documents are intentionally unchanged.
    if re.search(r'<link\b[^>]*rel=[\"\'][^\"\']*(?:icon)', old, flags=re.I):
        raise RuntimeError('Existing icons require review: '+name)
    new = re.sub(r'</head>', lambda m: block + m.group(0), old, count=1, flags=re.I)
    assert new.replace(block, '', 1) == old
    path.write_text(new)
    changed.append(name)
assert 'index.html' in changed or '<!-- Approved Open Close Map site icons -->' in (ROOT/'index.html').read_text()

# Server-rendered area/category/store pages already load this shared script.
# Install links without altering the existing GA4 or first-party PV code.
prefix = '''/* OCM_APPROVED_FAVICON_20260911: shared server-rendered page icons. */
(function(){
  'use strict';
  if(!document.head)return;
  const icons=[
    {rel:'icon',href:'/favicon.ico',type:'image/x-icon',sizes:'16x16 32x32 48x48'},
    {rel:'icon',href:'/favicon-96x96.png',type:'image/png',sizes:'96x96'},
    {rel:'apple-touch-icon',href:'/apple-touch-icon.png',sizes:'180x180'}
  ];
  for(const item of icons){
    if(document.querySelector('link[rel="'+item.rel+'"][href="'+item.href+'"]'))continue;
    const link=document.createElement('link');
    for(const [key,value] of Object.entries(item))link[key]=value;
    document.head.appendChild(link);
  }
})();
'''
path = ROOT/'analytics.js'
old = path.read_text()
if 'OCM_APPROVED_FAVICON_20260911' not in old:
    path.write_text(prefix + old)
    assert path.read_text()[len(prefix):] == old
    changed.append('analytics.js')

verification = {
    'approved_source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'resizing_only': True,
    'files': {name: {'sha256': hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), 'bytes': (ROOT/name).stat().st_size} for name in ['favicon.ico',*outputs]},
    'html_files': [n for n in paths if n and '<!-- Approved Open Close Map site icons -->' in (ROOT/n).read_text()],
    'shared_script_icons': True,
    'google_verification_files_changed': False
}
(ROOT/'docs/favicon-assets.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(verification,ensure_ascii=False,indent=2))
