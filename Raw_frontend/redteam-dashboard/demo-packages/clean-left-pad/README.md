# demo-clean-left-pad

A simple string padding utility, similar to left-pad.

This package only performs string manipulation. It does not access files,
network resources, subprocesses, or environment variables.

## Usage

```python
from clean_left_pad import pad_left, pad_right

assert pad_left("demo", 6, "0") == "00demo"
assert pad_right("demo", 6, ".") == "demo.."
```
