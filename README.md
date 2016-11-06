### typo

This package intends to provide run-time type checking for functions annotated 
with argument type hints (standard library `typing` module in Python 3.5, or 
`backports.typing` package in Python 3.3 / 3.4).

Example:

```python
from typing import Sequence, List
from typo import type_check

@type_check
def f(x: int, s: Sequence[int]) -> List[int]:
	...
```

The `@type_check` decorator ensures that the values passed to annotated
arguments will have their types checked before the function is executed;
return value can be optionally checked as well. 

If the value types are not consistent with the function signature, a 
`TypeError` with a descriptive error message will be raised:

```python
>>> f(1, (0, 2.2))
```

```
TypeError: invalid item #1 of `s`: expected int, got float
```

*Note:* this is work-in-progress and not all `typing` primitives are
supported; however all supported constructs should be covered by a
good number of tests.

Here's some of the supported type hints: simple types, `List`, `Dict`,
`Tuple`, `Sequence`, `Set`, `TypeVar` (with support for constraints 
and upper bounds).

What's not supported: `Iterator` and `Generator` (which we can't
inspect due to their laziness), `Callable` (which we can't check
without calling it), forward references (which is possible to
support but requires more work), covariant and contravariant
type variables (this requires more thought but isn't likely
to be helpful in the runtime context).