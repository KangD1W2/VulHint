#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__NAME__ = "VulHint"
__VERSION__ = "0.0.1"
__CREATOR__ = "md5_salt"

__AUTHOR__ = "Virink"
__DATA__ = "VulHint.json"
__SETTINGS__ = "VulHint.sublime-settings"

__DEBUG__ = 1

import sublime
import sublime_plugin
import re
import time

g_regions = []
g_region_lines = []
g_jump_index = 0
g_line_regions = {}


def debug_print(var):
    if __DEBUG__:
        print("===== DEBUG VulHint : %s===== " % str(time.time()))
        print(var)


class Vulhint(sublime_plugin.EventListener):
    """漏洞提示

    Show a tip for code by rules

    Extends:
        sublime_plugin.EventListener

    Variables:
        lang {str} -- 语言类型
        data {dict} -- [description]

        g_regions {list} -- [description]
        g_line_regions {dict} -- [description]
        g_region_lines {list} -- [description]
        g_jump_index {int} -- [description]

    """

    lang = None
    data = {}

    def init(self, view):
        global g_regions
        clear_mark(view)
        g_regions = []
        self.lang = self.guess_lang(view)
        self.data = sublime.load_settings("VulData.json").get(self.lang, {})
        debug_print("Language : " + self.lang)
        # debug_print(self.data)

    def on_load_async(self, view):
        debug_print('on_post_save_async')
        if not sublime.load_settings(__SETTINGS__).get("enable", 1):
            return
        self.init(view)
        self.mark_vul(view)
        get_lines(view)

    def on_post_save_async(self, view):
        debug_print('on_post_save_async')
        if not sublime.load_settings(__SETTINGS__).get("enable", 1):
            return
        global g_regions
        self.init(view)
        self.mark_vul(view)
        get_lines(view)

    def on_hover(self, view, point, hover_zone):
        debug_print('on_hover')
        if not sublime.load_settings(__SETTINGS__).get("enable", 1):
            return
        global g_regions
        global g_region_lines
        global g_jump_index
        global g_line_regions

        if not self.lang or not self.data:
            return
        # self.init(view)
        # locate smiles in the string. smiles string should be at the beginning and followed by tab (cxsmiles)
        # hovered_line_text = view.substr(view.word(point)).strip()
        #hovered_line_text = view.substr(view.line(point)).strip()
        if (hover_zone == sublime.HOVER_TEXT):
            word = view.substr(view.word(point)).strip()
            debug_print(word)
            for key in g_regions:
                val = self.data[key]
                if word in val["keyword"]:
                    hovered_text = '<p>%s</p>' % (val["discription"])
                    view.show_popup(hovered_text,
                                    flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                                    location=point)
                    g_jump_index = g_region_lines.index(view.rowcol(point)[0])
                    return
            line = view.rowcol(point)[0]
            if g_line_regions.get(line):
                hovered_text = ''
                for key in g_line_regions.get(line):
                    val = self.data[key]
                    hovered_text += '<p>%s</p><br>' % (val["discription"])
                view.show_popup(
                    hovered_text, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY, location=point)
                g_jump_index = g_region_lines.index(view.rowcol(point)[0])

        return

    def mark_vul(self, view):
        global g_regions
        if not self.lang or not self.data:
            return
        for key, val in self.data.items():
            if not val['enable']:
                continue
            # 处理规则
            pattern = val['pattern']
            pattern_1 = pattern
            pattern_2 = None
            if isinstance(pattern, list):
                pattern_1 = pattern[0]
                if len(pattern) > 2:
                    pattern_2 = pattern[1]
            # 通过正则表达式匹配漏洞
            vul = view.find_all(pattern_1, flags=re.IGNORECASE)
            if not vul:
                continue
            # 移除标志过的
            vul = [
                v for v in vul if '/*vvv*/' not in view.substr(view.line(v))]
            # TODO 二次判断
            # if pattern_2:
            #     _vul = re.findall(pattern_2, vul_str, flags=re.IGNORECASE)
            #     debug_print(_vul)
            #     if not _vul:
            #         continue
            view.add_regions(key, vul, "string", "cross",
                             sublime.DRAW_OUTLINED | sublime.DRAW_STIPPLED_UNDERLINE)
            g_regions.append(key)

    def guess_lang(self, view=None, path=None, sublime_scope=None):
        """根据后缀猜测语言类型

        Keyword Arguments:
            view {[type]} -- [description] (default: {None})
            path {[type]} -- [description] (default: {None})
            sublime_scope {[type]} -- [description] (default: {None})

        Returns:
            [str] -- 语言类型
        """
        if not view:
            return None
        filename = view.file_name()
        return filename.split('.')[-1].lower()


def clear_mark(view):
    global g_regions
    if not g_regions:
        return
    for i in g_regions:
        view.erase_regions(i)


def get_lines(view):
    global g_regions
    global g_region_lines
    global g_line_regions

    g_line_regions = {}
    g_region_lines = set()
    for region in g_regions:
        for i in view.get_regions(region):
            line = view.rowcol(i.a)[0]
            g_region_lines.add(line)
            if g_line_regions.get(line, None):
                g_line_regions[view.rowcol(i.a)[0]].add(region)
            else:
                g_line_regions[view.rowcol(i.a)[0]] = set([region])
    g_region_lines = sorted(g_region_lines)


class VulhintGotoNextCommand(sublime_plugin.TextCommand):
    """GotoNext VulHint Command

    跳的下一个

    Extends:
        sublime_plugin.TextCommand
    """

    def run(self, edit):
        global g_jump_index, g_region_lines
        # Convert from 1 based to a 0 based line number
        line = g_region_lines[g_jump_index]
        g_jump_index = (g_jump_index + 1) % len(g_region_lines)
        # Negative line numbers count from the end of the buffer
        if line < 0:
            lines, _ = self.view.rowcol(self.view.size())
            line = lines + line + 1
        pt = self.view.text_point(line, 0)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(pt))
        self.view.show(pt)


class VulhintEnableCommand(sublime_plugin.TextCommand):
    """Enable VulHint Command

    开启VulHint

    Extends:
        sublime_plugin.TextCommand
    """

    def run(self, edit):
        debug_print('Vulhint Disable Command')
        setting = sublime.load_settings(__SETTINGS__)
        status = int(setting.get("enable", 0))
        if status:
            debug_print('Disbale Vulhint')
        else:
            debug_print('Enable Vulhint')
        setting.set("enable", (status + 1) % 2)
        sublime.save_settings(__SETTINGS__)


class VulhintClearCommand(sublime_plugin.TextCommand):
    """Clear VulHint Command

    清空 VulHint

    Extends:
        sublime_plugin.TextCommand
    """

    def run(self, edit):
        debug_print('Vulhint Clear Command')
        clear_mark(self.view)
