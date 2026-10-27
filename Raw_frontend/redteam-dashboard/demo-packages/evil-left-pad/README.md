# demo-evil-left-pad

A simple string padding utility, similar to left-pad.

The module's padding functions only manipulate strings. For the defensive
demo, `SIMULATED_INSTALL_EVENTS` contains clearly marked sample file-read and
subprocess records. These records are inert: package installation and import
do not access files, start processes, or make network requests.

## Usage

```python
from evil_left_pad import SIMULATED_INSTALL_EVENTS, pad_left

assert pad_left("demo", 6, "0") == "00demo"
print(SIMULATED_INSTALL_EVENTS)
```
