# pyLMUSharedMemory (submodule)

Ce dossier doit contenir la librairie pyLMUSharedMemory de TinyPedal.

## Installation

```bash
# Depuis la racine du projet :
git submodule add https://github.com/TinyPedal/pyLMUSharedMemory.git pyLMUSharedMemory

# Ou manuellement, copier les fichiers depuis :
# https://github.com/TinyPedal/pyLMUSharedMemory
# Fichiers requis : lmu_data.py, lmu_enum.py, lmu_mmap.py, lmu_type.py, __init__.py
```

## Fichiers attendus

- `__init__.py`
- `lmu_data.py`   — ctypes structs (LMUObjectOut, etc.)
- `lmu_enum.py`   — enums LMU
- `lmu_mmap.py`   — MMapControl (lecture shared memory)
- `lmu_type.py`   — types de base
