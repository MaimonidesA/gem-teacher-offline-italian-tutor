#!/usr/bin/env python3
"""Install the approved additional Italian voice; normal app use stays offline."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = 'committa/it_IT-serena-high'
REVISION = 'c704759b2286f5f8c56eb4476169c4e2cda10b02'
BASE = f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/'
FILES = {
    'serena.onnx': ('it_IT-serena-high.onnx', '7462fbdf03727fb4c0c161286ad538fe6436b7e4b1c3059ef52930032475955f'),
    'serena.onnx.json': ('it_IT-serena-high.onnx.json', '60597bac737a20766591fe24d1315df9a3811dc3509e69bc394cdee19eccbae7'),
    'serena-MODEL_CARD.md': ('README.md', None),
}

def verified(path, checksum):
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == checksum

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, help='Copy previously downloaded files without network access')
    args = parser.parse_args()
    folder = ROOT / 'runtime/voices'
    folder.mkdir(parents=True, exist_ok=True)
    if all(verified(folder / ('it-' + name), checksum) for name, (_, checksum) in FILES.items() if checksum):
        print('Serena is already installed and verified.')
        return
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        temp = Path(temp)
        for name, (remote, checksum) in FILES.items():
            path = temp / name
            if args.source_dir:
                shutil.copyfile(args.source_dir / name, path)
            else:
                print(f'Downloading {remote}…', flush=True)
                with urllib.request.urlopen(BASE + remote, timeout=60) as response, path.open('wb') as output:
                    shutil.copyfileobj(response, output, length=1024 * 1024)
            if checksum and not verified(path, checksum):
                raise ValueError(f'Checksum mismatch for {name}; no voice files installed.')
        info = json.loads((temp / 'serena.onnx.json').read_text())
        if info.get('espeak', {}).get('voice') != 'it' or info.get('num_speakers') != 1:
            raise ValueError('Expected the single-speaker Italian Serena voice.')
        for name in FILES:
            (temp / name).replace(folder / ('it-' + name))
    (folder / 'it-serena-source.json').write_text(json.dumps({
        'author': 'committa', 'repository': f'https://huggingface.co/{REPOSITORY}',
        'revision': REVISION, 'license': 'CC-BY-4.0', 'modified': False,
        'files': {name: {'source': remote, 'sha256': sha} for name, (remote, sha) in FILES.items()},
    }, indent=2))
    print('Serena is ready for offline use. The retired Aurora and Leonardo models are not used.')

if __name__ == '__main__':
    main()
