# Snbtlib
[![PyPI version](https://badge.fury.io/py/snbtlib.svg)](https://badge.fury.io/py/snbtlib)

## Installation
```
pip install snbtlib
```

## Usage
```python
import snbtlib
from pathlib import Path

# Reading Text to JSON
json = snbtlib.loads(Path('quest.snbt').read_text(encoding='utf-8'))

# Dumping JSON to Text
text = snbtlib.dumps(json)
Path('quest.snbt').write_text(text, encoding='utf-8')
```