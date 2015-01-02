#!/usr/bin/env python
# -*- coding: utf-8 -*-

import invoke


@invoke.task
def test():
    invoke.run("nosetests -v")


@invoke.task
def bower():
    invoke.run("cd nbviewer/static && bower install")
