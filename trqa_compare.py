# -*- encoding: utf-8 *-*
from __future__ import print_function, unicode_literals
import sys

reload(sys)
sys.setdefaultencoding('utf8')
import codecs
import getopt
import spacy
import json
import re
from nltk.tokenize import word_tokenize, sent_tokenize
import logging
import editdistance
import os
import subprocess
import pdb

# ###################################################################################################
# Some Initialization here...
# ###################################################################################################
logging.basicConfig(filename='logfile.log', format='%(asctime)s: %(levelname)s: %(message)s')
logging.root.setLevel(level=logging.INFO)
language = 'de'
stdscr = None
screen_max_x = 0
screen_max_y = 0
screen_max_y, screen_max_x = os.popen('stty size').read().split()
screen_max_x = int(screen_max_x) - 1
screen_max_y = int(screen_max_y) - 1
if screen_max_x < 159:
    print('Please set your screen WIDTH to at least 160 characters, otherwise you will not be able to read text..')
    sys.exit(1)

import curses

try:
    from tkinter import *
    from tkinter import filedialog
except:
    from Tkinter import *
    import tkFileDialog as filedialog

undo_used = False

punkt_remover = re.compile(r'[.,;:"/?!@#$%&*()\-_=+\[\]\{\}~`<>`\n\t«»]+')
nlp = None
previous_strings = []
user_home = os.path.expanduser('~')
trqa_settings_dir = os.path.join(user_home, '.trqa')
if not os.path.exists(trqa_settings_dir):
    os.makedirs(trqa_settings_dir)
trqa_settings_file = os.path.join(trqa_settings_dir, 'trqa.settings')


# ###################################################################################################
# END OF Initialization here...
# ###################################################################################################
def init_curses():
    global stdscr
    global screen_max_x
    global screen_max_y

    stdscr = curses.initscr()
    stdscr.timeout(-1)
    curses.noecho()
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
        curses.init_pair(i + 1, i, -1)


def get_path_tk(title, file_type_desc, initial_dir='~'):
    global root
    root.update()
    filename = filedialog.askopenfilename(initialdir=initial_dir, title=title, filetypes=(file_type_desc,))
    root.update()
    if filename is not None and len(filename) == 0:
        filename = None
    return filename


def print_menu_at(menu_entries, x=0, y=1, color=250):
    global stdscr
    global screen_max_x

    stdscr.move(y, x)
    for entry in menu_entries:
        key = entry[0]
        text = entry[1]
        stdscr.addstr(key, curses.A_REVERSE)
        stdscr.addstr(': ', curses.color_pair(color))
        stdscr.addstr(text, curses.color_pair(color))
        stdscr.addstr('   ', curses.color_pair(color))
        stdscr.refresh()


def print_reverse_at(text, x=0, y=1, color=250, win=None):
    global stdscr

    if win == None:
        win = stdscr
    win.move(y, x)
    win.addstr(text, curses.A_REVERSE)
    win.refresh()


def print_strings_at(x, y, string1, string2=None, sep='|', primary_color=119, secondary_color=None, win=None):
    global stdscr
    global screen_max_x

    if win == None:
        window = stdscr
        max_x = screen_max_x
    else:
        window = win
        max_x = win.getmaxyx()[1]
    window.move(y, x)
    window.addstr(' ' * (max_x - x))
    window.refresh()
    window.move(y, x)
    window.addstr(string1, curses.color_pair(primary_color))
    if string2 is not None:
        stdscr.addstr(' | ')
        if secondary_color is not None:
            stdscr.addstr(string2, secondary_color)
        else:
            stdscr.addstr(string2)
    stdscr.refresh()


def run_modal_panel(texts, buttons, title=None, text_color=230, button_color=230):
    global stdscr
    global screen_max_x
    global screen_max_y

    max_str_len = 0
    for message_text in texts:
        if len(message_text) > max_str_len:
            max_str_len = len(message_text)
    button_total_length = 0
    allowed_chars = []
    max_button_size = 0
    for button in buttons:
        short_cut_i = button.find('_')
        if short_cut_i >= 0:
            short_cut = button[short_cut_i + 1].lower()
            if short_cut == '@':
                allowed_chars.append('\r')
                allowed_chars.append('\n')
            else:
                allowed_chars.append(short_cut)
        else:
            print('You can not do that...')
            sys.exit(1)
        button_total_length += len(button) + 2
        if max_button_size < len(button) + 2:
            max_button_size = len(button) + 2
    max_str_len += 2
    button_total_length = button_total_length + 10
    if max_str_len < button_total_length:
        max_str_len = button_total_length
    row_count = len(texts) + 4
    if title is not None:
        row_count += 2
    modal_panel = curses.newwin(row_count, max_str_len + 2, (screen_max_y - row_count) / 2, (screen_max_x - max_str_len) / 2)
    modal_panel.box()
    modal_panel.refresh()
    stdscr.refresh()
    print_panel_title(title, win=modal_panel)
    for i, text in enumerate(texts):
        row = i + 1
        if title is not None:
            row += 2
        print_strings_at(2, row, text, win=modal_panel, primary_color=text_color)
    space_per_button = max_button_size
    max_button_area = max_str_len - 10
    if len(buttons) == 1:
        spacing = max_button_area - (max_button_size * len(buttons))
    else:
        spacing = (max_button_area - (max_button_size * len(buttons))) / (len(buttons) - 1)
    for i, button in enumerate(buttons):
        button_short_cut_pos = button.find('_')
        button_short_cut = button[button_short_cut_pos + 1]
        if short_cut == '@':
            button_short_cut = '↵'
        button_left = button[:button_short_cut_pos]
        button_right = button[button_short_cut_pos + 2:]
        x_pos = i * space_per_button
        x_pos += spacing * i
        x_pos += 5
        print_strings_at(x_pos, row_count - 2, '[' + button_left, primary_color=button_color, win=modal_panel)
        print_reverse_at(button_short_cut, x=x_pos + 1 + len(button_left), y=row_count - 2, win=modal_panel)
        modal_panel.addstr(button_right + ']', curses.color_pair(button_color))
    ch = ''
    modal_panel.box()
    if len(allowed_chars) == 1:
        allowed_chars.append('\r')
        allowed_chars.append('\n')
    while ch not in allowed_chars:
        ch = modal_panel.getkey().lower()
    modal_panel.erase()
    modal_panel.refresh()
    del modal_panel
    stdscr.refresh()
    return ch


def print_string(string, color=119):
    global stdscr
    stdscr.addstr(string, curses.color_pair(color))
    stdscr.refresh()


def _print_string_hcentered_at(y, string, color=curses.A_NORMAL, clear_line=True, win=None):
    global stdscr
    global screen_max_x

    if win is None:
        win = stdscr
        max_x = screen_max_x
    else:
        max_x = win.getmaxyx()[1]
    if clear_line:
        x = 0
        win.move(y, x)
        win.addstr(' ' * (max_x - (x + 1)))
        win.refresh()
    x = (max_x - len(string)) // 2
    win.move(y, x)
    win.addstr(string, color)
    win.refresh()


def print_panel_title(string, win=None):
    global stdscr
    global screen_max_x

    if win is None:
        win = stdscr
        max_x = screen_max_x
    else:
        max_x = win.getmaxyx()[1]
    padding = max_x - len(string) - 1
    padding_half = padding // 2
    padding_rem = padding % padding_half
    pad_left = ' ' * padding_half
    pad_right = ' ' * (padding_half + padding_rem)
    string = pad_left + string + pad_right
    win.move(1, 1)
    win.addstr(string, curses.A_REVERSE)
    win.refresh()


def print_string_hcentered_reverse_at(y, string, clear_line=True, win=None):
    _print_string_hcentered_at(y, string, color=curses.A_REVERSE, clear_line=clear_line, win=win)


def print_string_hcentered_at(y, string, color=250, clear_line=True, win=None):
    _print_string_hcentered_at(y, string, color=curses.color_pair(color), clear_line=clear_line, win=win)


def print_block(block_length):
    global stdscr
    string = ' ' * block_length
    stdscr.addstr(string, curses.A_REVERSE)
    stdscr.refresh()


def print_block_at(x, y, block_length):
    global stdscr
    stdscr.move(y, x)
    print_block(block_length)


def print_title(title):
    print_string_hcentered_at(0, title, color=219)


def simple_tokenize(line):
    global language
    line = punkt_remover.sub(' ', line)
    repl_char = ' '
    if language == 'uk' or language == 'ru':
        repl_char = 'Ä'
    line = line.replace('\'', repl_char)
    return word_tokenize(line)


def find_best_match_for_user(t_transcription, t_transcription_pp, t_transcription_nlp, sliced_transcription):
    dist = editdistance.eval(' '.join(t_transcription_pp), sliced_transcription)
    book_w_nlp = nlp(sliced_transcription)
    sim = t_transcription_nlp.similarity(book_w_nlp)
    logging.info('{} -> {} : LD={}, SIM={}'.format(t_transcription, sliced_transcription, dist, sim))
    return dist, sim


def show_help():
    message = [
        'Your job is to select the correct text from the original book (Bookw.)',
        '',
        'Blue text is the automatic transcription. Green Text is recommendation  from',
        'original text. Your job is to move the "pointer" of green text by "guessing"',
        'what the automatic  transcription  could actually mean. You do this with "+"',
        'and "-". Once  you are  satisfied, please  hit <ENTER> to accept  it. If you',
        'made a  mistake,  you can  use "U" to undo  the  last  change.',
        '',
        'Sometimes the transcription will not  be  at all in the  original text. This',
        'usually happens at the beginning of the  QA-task. Just  hit "K" to  keep the',
        'transcription...',
        'Also, sometimes  there is "original" text  that is not transcribed. In these',
        'cases, it may just be comment. Select the  words and hit "S" to skip them...',
        '',
        'COMMANDS:',
        '    +: Include next word from book',
        '    -: Remove last word',
        '    U: Go back one transcription',
        '    K: Keep transcription text as is',
        '    S: Skip the selected words in the book',
        '    <ENTER>: Accept proposal',
        '    Q: Quit Application'
    ]
    title = 'Help'
    buttons = ['_OK, Thanks']
    run_modal_panel(message, buttons, title)


def ask_user(t_transcription, sliced_transcr=None, audio_filename=None):
    global stdscr
    global screen_max_x
    global screen_max_y
    global previous_strings
    global undo_used
    keep_original = False
    menu = [('U', 'Undo Last'), ('S', 'Skip as error'), ('↵', 'Accept'), ('J', 'Play Audio'), ('Q', 'Quit'), ('?', 'Help')]

    print_menu_at(menu, x=1, color=230)
    y_pos_t = screen_max_y - 3
    max_text = y_pos_t - 4
    text_col_start = 12
    correct = False

    print_strings_at(0, y_pos_t - 1, '-' * (screen_max_x + 1), primary_color=250)
    max_history_show = min(len(previous_strings), max_text)
    history_to_show = previous_strings[len(previous_strings) - max_history_show:]
    for i, entry in enumerate(history_to_show):
        entry = entry[:min(len(entry), screen_max_x - 1)]
        print_strings_at(0, y_pos_t - max_history_show + i - 1, entry, primary_color=250)
    orig_space = screen_max_x - 3 - text_col_start
    if len(t_transcription) > screen_max_x - text_col_start:
        orig_space -= 5 + text_col_start
        left = orig_space // 2
        right = orig_space // 2
        transc_text = t_transcription[:left]
        transc_text += ' ... '
        transc_text += t_transcription[max(-(len(t_transcription) - left), -right):]
    else:
        transc_text = t_transcription
    print_strings_at(0, y_pos_t, 'ASSUMPTION: ', primary_color=209)
    print_strings_at(0, y_pos_t + 1, 'CORRECTION: ', primary_color=209)
    print_strings_at(text_col_start, y_pos_t, transc_text, primary_color=46)
    char = ''

    while char != '\n' and char != '\r':
        f_str = sliced_transcr
        if len(f_str) > screen_max_x - text_col_start:
            orig_space = int((screen_max_x - text_col_start) * 0.7)
            orig_space -= 5
            left = orig_space // 2
            right = orig_space // 2
            t_str = f_str[:left] + ' ... ' + f_str[max(-(len(f_str) - left), -right):]
            f_str = t_str
        print_strings_at(text_col_start, y_pos_t + 1, f_str)

        char = stdscr.getkey()

        correct_key_used = False

        if char == '\n' or char == '\r':
            correct_key_used = True
            undo_used = False
            correct = True
        elif char.lower() == 'u':
            correct_key_used = True
            undo_used = True
        elif char.lower() == 'q':
            if run_modal_panel(['Are you sure you want to quit? You were doing such', 'a great job...'], ['_Quit', '_Continue'], title='Quit now?') == 'q':
                curses.endwin()
                sys.exit(0)
        elif char.lower() == 's':
            correct_key_used = True
            correct = False
        elif char == '?':
            show_help()
        elif char == 'j':
            play_audio(audio_filename)

        if char != 'j' and correct_key_used:
            return correct, undo_used


def compare_transcription(t_transcription_orig, sliced_transcr, manually=False, audio_filename=None):
    global nlp
    go_prev = False
    correct = False
    sim_th = 0.7
    book_pp = simple_tokenize(sliced_transcr)
    t_sliced_transcr = ' '. join(book_pp)
    t_transcription_pp = simple_tokenize(t_transcription_orig)
    t_transcription = ' '.join(t_transcription_pp)
    t_transcription_nlp = nlp(t_transcription.lower())
    recognize_automatically = not manually

    if recognize_automatically:
        min_dist, max_sim = find_best_match_for_user(t_transcription, t_transcription_pp, t_transcription_nlp, t_sliced_transcr)
        if max_sim > sim_th or min_dist < 5:
            correct = True

    if correct is False:
        correct, go_prev = ask_user(t_transcription_orig, sliced_transcr=t_sliced_transcr, audio_filename=audio_filename)
    return correct, go_prev


def get_audiofile_full_path(filename):
    result = None

    project_root_dir = os.path.dirname(trqa_settings['last_project']['json_file'])
    for root, dirs, files in os.walk(project_root_dir):
        for file in files:
            if file == filename:
                result = (os.path.join(root, file))
                return result
    return result


def play_audio(filename=None):
    error_happened = True
    if filename is not None:
        audio_filepath = get_audiofile_full_path(filename)
        if audio_filepath is not None:
            error_happened = False
            subprocess.Popen(["afplay", audio_filepath])
    if error_happened:
        print('\x07', end='')
        sys.stdout.flush()


def convert_and_clean_protocol(protocol):
    tmp_res = protocol
    if protocol is not None:
        if not isinstance(protocol, dict):
            result = {}
            for entry in protocol:
                key = entry.keys()[0]
                value = entry[key]
                transc = value[0].keys()[0]
                result[key] = transc
            converted = True
        else:
            result = {}
            for key in tmp_res.keys():
                value = tmp_res[key]
                key = os.path.basename(key)
                result[key] = value
    return result


def perform_qa(json_file, aeneas_results_file, out_file, use_history):
    global screen_max_x
    global screen_max_y
    global trqa_settings
    global trqa_settings_file
    global previous_strings
    global language
    global undo_used

    go_prev = False
    progress_bar_width = 60
    previous_strings = []
    cleanly_finished = False

    print_title('***** M-AILABS Transcription QA v1.2 *****')
    print_strings_at(0, 2, '-' * (screen_max_x + 1), primary_color=250)

    if use_history:
        history_json = json.load(codecs.open(out_file, 'r', 'utf-8'))
        json_history = {}
        for a in history_json:
            key = a.keys()[0]
            json_history[key] = a[key]
            previous_strings.append(a[key])
        out_json = history_json
    else:
        out_json = []

    transcriptions = json.load(codecs.open(json_file, 'r', 'utf-8'))
    transcriptions = convert_and_clean_protocol(transcriptions)
    json.dump(transcriptions, codecs.open(json_file, 'w', 'utf-8'), indent=4)

    sliced_json = json.load(codecs.open(aeneas_results_file, 'r', 'utf-8'))

    sliced_dict = {}
    for entry in sliced_json['fragments']:
        s_text = entry['lines']
        s_key = entry['id'] + '.mp3'
        sliced_dict[s_key] = s_text[0]

    # if language == 'uk' or language == 'ru':
    #     book = book.replace('\'', 'Ä')

    i = 0

    tkeys = transcriptions.keys()
    tkeys.sort()

    if use_history and len(out_json) > 0:
        # pdb.set_trace()
        last_key = out_json[-1].keys()[0]
        i = tkeys.index(last_key)+1

    len_t = len(tkeys)
    logging.info('{}'.format(tkeys))
    while i < len(tkeys):
        key = tkeys[i]
        t_text = transcriptions[key]
        sliced_text = sliced_dict[key]
        i += 1
        print_strings_at(0, screen_max_y - 1, '-' * (screen_max_x + 1), primary_color=250)
        file_name = key

        fname_only = os.path.basename(file_name)
        fname_message = 'CURRENT FILE: ' + fname_only
        done_pe = int(float(progress_bar_width) / float(len_t) * float(i))
        print_strings_at(0, screen_max_y, '{:3.2f}% ['.format(float(i) / float(len_t) * 100), primary_color=230)
        print_block(done_pe)
        print_string('{}] {:d}/{:d}'.format(' ' * (progress_bar_width - done_pe), i, len_t), color=230)
        print_strings_at(screen_max_x - len(fname_message), screen_max_y, fname_message, primary_color=230)

        correct, go_prev = compare_transcription(t_text,
                                                 sliced_transcr=sliced_text,
                                                 manually=undo_used,
                                                 audio_filename=fname_only)
        if correct is False and go_prev is False:  # file is incorrect - skip it
            continue

        if go_prev:
            if len(out_json) > 0:
                del out_json[-1]
                json.dump(out_json, codecs.open(out_file, 'w', 'utf-8'), indent=4)
            else:
                print('\x07', end='')
                sys.stdout.flush()
            break
        if correct:
            out_dict = {fname_only: sliced_text}
            out_json.append(out_dict)
            json.dump(out_json, codecs.open(out_file, 'w', 'utf-8'), indent=4)
            previous_strings.append(sliced_text)

            if i >= len(tkeys):
                trqa_settings['finished'] = 1
                if 'last_project' in trqa_settings:
                    del trqa_settings['last_project']
                json.dump(trqa_settings, codecs.open(trqa_settings_file, 'w', 'utf-8'), indent=4)
                cleanly_finished = True
                break
        else:
            break
    json.dump(out_json, codecs.open(out_file, 'w', 'utf-8'), indent=4)
    return go_prev, cleanly_finished


def run_qa(json_file, aeneas_file, out_file, use_history):
    global root
    global trqa_settings
    global stdscr

    continue_last_project = False
    done_for_today = False
    if os.path.exists(trqa_settings_file):
        trqa_settings = json.load(codecs.open(trqa_settings_file, 'r', 'utf-8'))
    else:
        trqa_settings = {'last_dir': '~', 'finished': 0}
    initial_dir = trqa_settings['last_dir']
    if trqa_settings['finished'] == 1:
        initial_dir = os.path.dirname(initial_dir)
    if 'last_project' in trqa_settings and trqa_settings['finished'] != 1:
        last_project = trqa_settings['last_project']
        modal_ret = run_modal_panel([
            'Welcome to Transcription QA.',
            '',
            'You will first  choose a JSON-file and then a .txt-file. The JSON-file',
            'contains the  transcriptions generated by  a machine and the .txt-file',
            'contains the original text.',
            '',
            'Your job, if you  choose to accept it, is to find the correct original',
            'text for each transcription.',
            '',
            'Would you like to continue your  last project or start a  new project?',
            'Your last project was: [' + os.path.basename(os.path.dirname(trqa_settings['last_project']['json_file'])) + ']'],
                ['_Quit', '_Continue Last', 'Start _New'],
                'Continue Last Project')
        if modal_ret == 'q':
            return True, False
        continue_last_project = modal_ret == 'c'
        if continue_last_project:
            json_file = last_project['json_file']
            aeneas_file = last_project['aeneas_file']
            out_file = last_project['out_file']
            use_history = True
    else:
        continue_last_project = False
        modal_ret = run_modal_panel([
            'Welcome to Transcription QA.',
            '',
            'You will first  choose a JSON-file and then a .txt-file. The JSON-file',
            'contains the  transcriptions generated by  a machine and the .txt-file',
            'contains the original text.',
            '',
            'Your job, if you  choose to accept it, is to find the correct original',
            'text for each transcription.',
            '',
            'As usual, this message will self-destruct in 5 seconds (just kidding)!',
            '',
            'Thanks for helping us...'], ['_Quit', '_Accept'], title='Transcription QA')
        if modal_ret == 'q':
            return True, False
    while not done_for_today:
        root = Tk()
        root.withdraw()
        if not continue_last_project:
            if json_file is None:
                json_file = get_path_tk('Choose JSON Protocol', ('JSON Files', '*.json'), initial_dir=initial_dir)
                if json_file is None:
                    sys.exit(1)
            initial_dir = os.path.dirname(json_file)
            if aeneas_file is None:
                aeneas_file = get_path_tk('Choose sliced json', ('JSON Files', '*.json'), initial_dir=initial_dir)
                if aeneas_file is None:
                    sys.exit(1)
        root.destroy()
        del root
        trqa_settings['last_dir'] = initial_dir
        trqa_settings['finished'] = 0
        if out_file is None:
            out_file = 'alignments.json'
        out_file = os.path.join(os.path.dirname(json_file), out_file)
        trqa_settings['last_project'] = {'json_file': json_file, 'aeneas_file': aeneas_file, 'out_file': out_file}
        json.dump(trqa_settings, codecs.open(trqa_settings_file, 'w', 'utf-8'), indent=4)
        if not os.path.exists(out_file):
            use_history = False
        if json_file is not None and aeneas_file is not None and out_file is not None:
            stdscr.clear()
            stdscr.refresh()
            go_prev = True
            logging.info('============================================ STARTING NEW SESSION {}, {}'.format(json_file, aeneas_file))
            while go_prev:
                go_prev, cleanly_finished = perform_qa(json_file, aeneas_file, out_file, use_history)
                if go_prev:
                    use_history = True
                    stdscr.clear()
            if cleanly_finished:
                title = 'QA DONE'
                message = [
                    'This QA-session is finished. Thank you for your',
                    'cooperation.', '',
                    'Would you like to perform another QA-session?']
                buttons = ['_No Thanks', '_Yes, of course']
                retval = run_modal_panel(message, buttons, title, text_color=230, button_color=119)
                if retval == 'n':
                    done_for_today = True
                else:
                    continue_last_project = False
                    json_file = None
                    aeneas_file = None
                    use_history = True
                    out_file = None


if __name__ == '__main__':
    try:
        options, arguments = getopt.getopt(sys.argv[1:], 'j:b:o:rl:', ['--json', '--book', '--out', '--reset', '--language'])
    except getopt.GetoptError:
        print('Usage:')
        print('\tpython trqa.py -j <jsonfile> -b <bookfile> -o <outfile> [-r] [-l <language>')
        sys.exit(1)
    json_file = None
    aeneas_file = None
    out_file = None
    use_history = True
    language = 'de'
    for opt, arg in options:
        if opt in ('-j', '--json'):
            json_file = arg
        elif opt in ('-b', '--book'):
            aeneas_file = arg
        elif opt in ('-o', '--out'):
            out_file = arg
        elif opt in ('-r', '--reset'):
            use_history = False
        elif opt in ('-l', '--language'):
            language = arg.lower()
    init_curses()
    stdscr.clear()
    stdscr.refresh()
    nlp = spacy.load('de')
    run_qa(json_file, aeneas_file, out_file, use_history)
    stdscr.clear()
    curses.endwin()
