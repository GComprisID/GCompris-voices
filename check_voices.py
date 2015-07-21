#!/usr/bin/python
#
# GCompris - check_voices.py
#
# Copyright (C) 2015 Bruno Coudoin <bruno.coudoin@gcompris.net>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, see <http://www.gnu.org/licenses/>.
#
#
# The output is in markdown. A web page can be generated with:
# ./check_voices.py ../gcompris-kde  | markdown_py -x markdown.extensions.tables -x markdown.extensions.toc | ./check_voices_to_html.sh > voices_stats.html
#
# (Requires python-markdown to be installed)
#
import os
import sys
import re
import json
from pprint import pprint
import polib
import codecs
import locale

if len(sys.argv) < 2:
    print "Usage: check_voices.py [-v] path_to_gcompris"
    print "  -v:  verbose, show also files that are fine"
    print "  -nn: not needed, show extra file in the voice directory"
    sys.exit(1)

verbose = '-v' in sys.argv
notneeded = '-nn' in sys.argv
gcompris_qt = sys.argv[1]

# Force ouput as UTF-8
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

# A global has to hold a description on a key file like the UTF-8 char of
# the file.
descriptions = {}

def title1(title):
    print title
    print '=' * len(title)
    print ''

def title2(title):
    print title
    print '-' * len(title)
    print ''

def title3(title):
    print '### ' + title
    print ''


def get_intro_from_code():
    '''Return a set for activities as found in GCompris ActivityInfo.qml'''

    activity_info = set()

    activity_dir = gcompris_qt + "/src/activities"
    for activity in os.listdir(activity_dir):
        # Skip unrelevant activities
        if activity == 'template' or \
           activity == 'menu' or \
           not os.path.isdir(activity_dir + "/" + activity):
            continue

        try:
            with open(activity_dir + "/" + activity + "/ActivityInfo.qml") as f:
                activity_info.add(activity + '.ogg')
                # TODO if we want to grab the string to translate
                #content = f.readlines()
                #for line in content:
                #    m = re.match('.*intro:.*\"(.*)\"', line)
                #    if m:
                #        # Intro voice is in m.group(1)
                #        break
        except IOError as e:
            pass

    return activity_info

def init_intro_description_from_code():
    '''Init the intro description as found in GCompris ActivityInfo.qml'''
    '''in the global descriptions hash'''

    activity_dir = gcompris_qt + "/src/activities"
    for activity in os.listdir(activity_dir):
        # Skip unrelevant activities
        if activity == 'template' or \
           activity == 'menu' or \
           not os.path.isdir(activity_dir + "/" + activity):
            continue

        try:
            with open(activity_dir + "/" + activity + "/ActivityInfo.qml") as f:
                content = f.readlines()
                for line in content:
                    m = re.match('.*intro:.*\"(.*)\"', line)
                    if m:
                        descriptions[activity + '.ogg'] = m.group(1)
                        break

            if not descriptions.has_key(activity + '.ogg'):
                print "**ERROR: Missing intro tag in %s**" %(activity + "/ActivityInfo.qml")
        except IOError as e:
            pass

    print ''


def get_locales_from_config():
    '''Return a set for locales as found in GCompris src/core/LanguageList.qml'''

    locales = set()

    source = gcompris_qt + "/src/core/LanguageList.qml"
    try:
        with open(source) as f:
            content = f.readlines()
            for line in content:
                m = re.match('.*\"locale\":.*\"(.*)\"', line)
                if m:
                    locale = m.group(1).split('.')[0]
                    if locale != 'system' and locale != 'en_US':
                        locales.add(locale)
    except IOError as e:
        print "ERROR: Failed to parse %s: %s" %(source, e.strerror)

    return locales


def get_locales_from_po_files():
    '''Return a set for locales for which we have a po file '''
    '''Run make getSvnTranslations first'''

    locales = set()

    locales_dir = gcompris_qt + "/po"
    for locale in os.listdir(locales_dir):
        locales.add(locale.split('_', 1)[1][:-3])

    return locales

def get_translation_status_from_po_files():
    '''Return the translation status from the po file '''
    '''For each locale as key we provide a list: '''
    ''' [ translated_entries, untranslated_entries, fuzzy_entries, percent ]'''
    '''Run make getSvnTranslations first'''

    locales = {}

    locales_dir = gcompris_qt + "/po"
    for locale_file in os.listdir(locales_dir):
        locale = locale_file.split('_', 1)[1][:-3]
        po = polib.pofile(locales_dir + '/' + locale_file)
        # Calc a global translation percent
        percent = 1 - \
            (float((len(po.untranslated_entries()) +
                    len(po.fuzzy_entries()))) /
             (len(po.translated_entries()) +
              len(po.untranslated_entries()) +
              len(po.fuzzy_entries())))
        locales[locale] = \
            [ len(po.translated_entries()),
              len(po.untranslated_entries()),
              len(po.fuzzy_entries()),
              percent ]

        # Save the translation team in the global descriptions
        if po.metadata.has_key('Language-Team'):
            descriptions[locale] = po.metadata['Language-Team']
        else:
            descriptions[locale] = ''

    return locales

def get_words_from_code():
    '''Return a set for words as found in GCompris content-<locale>.json'''
    try:
        with open(gcompris_qt + '/src/activities/imageid/resource/content-' + locale + '.json') as data_file:
            data = json.load(data_file)
    except:
        print ''
        print "**ERROR: missing resource file %s**" %(gcompris_qt + '/src/activities/imageid/resource/content-' + locale + '.json')
        print ''
        return set()

    # Consolidate letters
    words = set()
    for word in data.keys():
        words.add(word)

    return words

def get_files(locale, voiceset):
    to_remove = set(['README'])
    try:
        return set(os.listdir(locale + '/' + voiceset)) - to_remove
    except:
        return set()

def get_locales_from_file():
    locales = set()
    for file in os.listdir('.'):
        if os.path.isdir(file) \
           and not os.path.islink(file) \
           and file[0] != '.':
            locales.add(file)

    return locales

def get_gletter_alphabet():
    try:
        with open(gcompris_qt + '/src/activities/gletters/resource/default-' + locale + '.json') as data_file:
            data = json.load(data_file)
    except:
        print ''
        print "**ERROR: Missing resource file %s**" %(gcompris_qt + '/src/activities/gletters/resource/default-' + locale + '.json')
        print ''
        return set()

    # Consolidate letters
    letters = set()
    for level in data['levels']:
        for w in level['words']:
            multiletters = ""
            for one_char in w.lower():
                multiletters += 'U{:04X}'.format(ord(one_char))
            letters.add(multiletters + '.ogg')
            descriptions[multiletters + '.ogg'] = w.lower()

    return letters

def diff_set(title, code, files):

    if not code and not files:
        return

    title2(title)

    if verbose and code & files:
        title3("These files are correct")
        print '| File | Description |'
        print '|------|-------------|'
        sorted = list(code & files)
        sorted.sort()
        for f in sorted:
            if descriptions.has_key(f):
                print '| %s | %s |' %(f, descriptions[f])
            else:
                print '|%s |  |' %(f)
        print ''

    if code - files:
        title3("These files are missing")
        print '| File | Description |'
        print '|------|-------------|'
        sorted = list(code - files)
        sorted.sort()
        for f in sorted:
            if descriptions.has_key(f):
                print '| %s | %s |' %(f, descriptions[f])
            else:
                print '|%s |  |' %(f)
        print ''

    if notneeded and files - code:
        title3("These files are not needed")
        print '| File | Description |'
        print '|------|-------------|'
        sorted = list(files - code)
        sorted.sort()
        for f in sorted:
            if descriptions.has_key(f):
                print '|%s | %s|' %(f, descriptions[f])
            else:
                print '|%s |  |' %(f)
        print ''

def diff_locale_set(title, code, files):

    if not code and not files:
        return

    title2(title)
    if verbose:
        title3("We have voices for these locales:")
        missing = []
        for locale in code:
            if os.path.isdir(locale):
                print '* ' + locale
            else:
                # Shorten the locale and test again
                shorten = locale.split('_')
                if os.path.isdir(shorten[0]):
                    print '* ' + locale
                else:
                    missing.append(locale)
    print ''
    print "We miss voices for these locales:"
    for f in missing:
        print '* ' + f
    print ''

def check_locale_config(title, stats, locale_config):
    '''Display and return locales that are translated above a fixed threshold'''
    title2(title)
    LIMIT = 0.8
    sorted_config = list(locale_config)
    sorted_config.sort()
    good_locale = []
    for locale in sorted_config:
        if stats.has_key(locale):
            if stats[locale][3] < LIMIT:
                print "* %s" %(locale)
            else:
                good_locale.append(locale)
        else:
            # Shorten the locale and test again
            shorten = locale.split('_')[0]
            if stats.has_key(shorten):
                if stats[shorten][3] < LIMIT:
                    print "* %s" %(locale)
                else:
                    good_locale.append(shorten)
            else:
                print "* %s no translation at all" %(locale)

    print ''
    print 'There is %d locales above %d%% translation: %s' %(len(good_locale), LIMIT * 100,
                                                           ' '.join(good_locale))

    return good_locale

#
# main
# ===

print '[TOC]'
print ''

stats = get_translation_status_from_po_files()
check_locale_config("Locales to remove from LanguageList.qml (translation level < 80%)",
                    stats, get_locales_from_config())

init_intro_description_from_code()

# Calc the big list of locales we have to check
all_locales = get_locales_from_po_files() | get_locales_from_file()

for locale in all_locales:
    title1(u'{:s} ({:s})'.format(locale, (descriptions[locale] if descriptions.has_key(locale) else '')))

    diff_set("Intro ({:s}/intro/)".format(locale), get_intro_from_code(), get_files(locale, 'intro'))
    diff_set("Letters ({:s}/alphabet/)".format(locale), get_gletter_alphabet(), get_files(locale, 'alphabet'))
    diff_set("Misc ({:s}/misc/)".format(locale), get_files('en', 'misc'), get_files(locale, 'misc'))
    diff_set("Colors ({:s}/colors/)".format(locale), get_files('en', 'colors'), get_files(locale, 'colors'))
    diff_set("Geography ({:s}/geography/)".format(locale), get_files('en', 'geography'), get_files(locale, 'geography'))
    diff_set("Words ({:s}/words/)".format(locale), get_words_from_code(), get_files(locale, 'words'))


