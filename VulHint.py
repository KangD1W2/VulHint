#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__NAME__ = "VulHint"
__VERSION__ = "0.1.1"
__CREATOR__ = "md5_salt"

__AUTHOR__ = "Virink"
__DATA__ = "VulData.json"
__SETTINGS__ = "VulHint.sublime-settings"

import time
import re
import os
import sublime_plugin
import sublime

DEBUG = sublime.load_settings(__SETTINGS__).get("debug", 0) != 0

g_regions = []
g_region_lines = []
g_jump_index = 0
g_line_regions = {}
rulesData = sublime.load_settings(__DATA__)


def debug_print(var):
    if DEBUG:
        print("====== DEBUG VulHint : ====== ")
        print(var)
        print("=============================")


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
        if self.lang in ['html', 'htm']:
            self.lang = 'js'
        self.data = rulesData.get(self.lang, {})
        debug_print("Language : " + self.lang)

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
        debug_print('mark_vul')
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
            # vul = [
            #     v for v in vul if '/*vvv*/' not in view.substr(view.line(v))]
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

    def on_pre_close(self, view):
        debug_print('on_pre_close')

    def on_close(self, view):
        debug_print('on_close')

    def on_activated(self, view):
        debug_print('on_activated')


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


class VulhintJumpToCommand(sublime_plugin.TextCommand):
    """JumpTo VulHint Command
    """

    def run(self, edit):
        view = self.view
        current_point = view.sel()[0].a
        debug_print(current_point)
        line = ''
        while current_point > 0:
            current_point -= 1
            line = view.substr(view.line(current_point))
            if '[+]' in line:
                debug_print(line)
                break
        m = re.findall(r'\[\+\] (.*?):(\d+)', line)
        view.window().open_file("%s:%s" %
                                (m[0][0], m[0][1]), sublime.ENCODED_POSITION)


class VulhintEnableCommand(sublime_plugin.TextCommand):
    """Enable VulHint Command

    开启VulHint

    Extends:
        sublime_plugin.TextCommand
    """

    def run(self, edit):
        debug_print('Vulhint Enable/Disable Command')
        setting = sublime.load_settings(__SETTINGS__)
        status = int(setting.get("enable", 0))
        if status:
            debug_print('Disbale Vulhint')
        else:
            debug_print('Enable Vulhint')
        setting.set("enable", (status + 1) % 2)
        sublime.save_settings(__SETTINGS__)


class VulhintDebugCommand(sublime_plugin.TextCommand):
    """VulHint Debug Command

    开启/关闭 Debug

    Extends:
        sublime_plugin.TextCommand
    """

    def run(self, edit):
        debug_print('Vulhint Debug Command')
        setting = sublime.load_settings(__SETTINGS__)
        status = int(setting.get("debug", 0))
        if status:
            debug_print('Disbale Debug')
        else:
            debug_print('Enable Debug')
        setting.set("debug", (status + 1) % 2)
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


class VulhintFindVulCommand(sublime_plugin.TextCommand):
    """Find Vul Command

    搜索漏洞

    Extends:
        sublime_plugin.TextCommand
    """
    _ext = False
    _lang = False

    def walk(self, path):
        all_files = []
        for root, dirs, files in os.walk(path):
            for f in files:
                if not self._ext or os.path.splitext(f)[1] in self._ext:
                    all_files.append(os.path.join(root, f))
        return all_files

    def findVuls(self, files, lang):
        if not lang:
            return
        rules = rulesData.get(lang, {})
        results = []
        for f in files:
            with open(f, 'r', encoding='utf-8') as fp:
                lines = fp.readlines()
                linesLen = len(lines)
                for r in rules:
                    num = -1
                    for line in lines:
                        num += 1
                        start = 0 if num < 3 else num - 3
                        end = num+4 if num+4 <= linesLen else linesLen
                        if re.findall(rules[r]['pattern'], line, re.I):
                            results.append("[+] %s:%d" % (f, num))
                            results.append("[*]" + rules[r]['discription'])
                            for i in range(start, end):
                                results.append(
                                    ("%d: \t%s" % (i, lines[i])).strip())
                            results.append("")
        return '\n'.join(results)

    def run(self, edit):
        debug_print('Vulhint Find Vul Command')
        w = self.view.window()
        extract_variables = w.extract_variables()
        project_path = extract_variables['folder']
        # debug_print(extract_variables)
        debug_print("[+] Project: "+project_path)
        files = self.walk(project_path)
        vuls_results = self.findVuls(files, self._lang)
        debug_print(vuls_results)
        results_view = w.new_file()
        results_view.set_name("Vuls Results")
        results_view.insert(edit, 0, vuls_results)
        results_view.set_read_only(True)
        w.focus_view(results_view)


class VulhintFindVulPhpCommand(VulhintFindVulCommand):
    """Find Vul of PHP
    """
    _ext = ['.php']
    _lang = 'php'


# class VulhintFindVulJavaCommand(VulhintFindVulCommand):
#     """Find Vul of Java
#     """
#     _ext = ['.java', '.jsp']
#     _lang = 'java'


class VulhintFindVulPyCommand(VulhintFindVulCommand):
    """Find Vul of Python
    """
    _ext = ['.py']
    _lang = 'py'


class VulhintFindVulJsCommand(VulhintFindVulCommand):
    """Find Vul of Python
    """
    _ext = ['.js', 'htm', 'html']
    _lang = 'js'
