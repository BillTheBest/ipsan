# -*-coding: utf-8 -*-


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    GRAY = '\033[90m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def _show(msg, style):
    print(style + msg + bcolors.ENDC)


def show_warning(msg=''):
    _show(msg, bcolors.WARNING)


def show_fail(msg=''):
    _show(msg, bcolors.FAIL)


def show_info(msg=''):
    _show(msg, bcolors.OKGREEN)


def show_disable(msg=''):
    _show(msg, bcolors.GRAY)


def show_bold(msg='', color=bcolors.OKGREEN):
    _show(msg, bcolors.BOLD)


def show_underline(msg='', color=bcolors.OKGREEN):
    _show(msg, bcolors.UNDERLINE)


def format_input_text(text, style=bcolors.UNDERLINE):
    return bcolors.OKBLUE + text + bcolors.ENDC

def format_confim_text(text):
    return bcolors.FAIL + text+'[y/n]? ' + bcolors.ENDC
