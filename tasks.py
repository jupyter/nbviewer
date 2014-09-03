#!/usr/bin/env python
# -*- coding: utf-8 -*-

import invoke

@invoke.task
def test():
    invoke.run("nosetests -v")
