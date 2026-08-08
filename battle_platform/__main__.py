#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""允许 `python -m battle_platform <subcommand>` 直接运行。"""

import sys
from battle_platform.cli import main

if __name__ == "__main__":
    main(sys.argv[1:])
