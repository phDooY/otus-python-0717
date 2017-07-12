#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import csv
import gzip
import json
import numpy as np
import re
import os

# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def get_last_log(log_dir):
    '''
    Takes directory to parse for logs, returns two values:
      name of last log file, and date str in format YYYYMMDD
    :param log_dir: 
    :return: (log_file_path, log_date) -> (str, str)
    '''
    files = os.listdir(log_dir)
    files_dates = [{'date': re.findall('\d+', f)[0], 'file_name': f} for f in files]
    last_log = sorted(files_dates, key=lambda x: int(x['date']), reverse=True)[0]
    last_log_date = last_log['date']
    last_log_file_path = log_dir + '/' + last_log['file_name']
    return last_log_date, last_log_file_path


def exists_last_report(name, reports_dir):
    files = os.listdir(reports_dir)
    if name + '.json' in files or \
        name + '.html' in files:
        return True
    else:
        return False


def parse_args():
    parser = argparse.ArgumentParser(description='Get script parameters.')
    parser.add_argument('-j', '--json',
                        help='Provide output in JSON format rather than HTML.',
                        action='store_true')
    parser.add_argument('--log_path',
                        help='Specific path to take log from.')
    return parser.parse_args()


def log_parser(csv_object):
    result = {}
    counter = 0
    time_counter = 0
    for row in csv_object:
        row_array = ''.join(row).split()
        url = row_array[6]
        request_time = float(row_array[-1])
        if not result.get(url):
            result[url] = [request_time]
        else:
            result[url].append(request_time)
        counter += 1
        time_counter += request_time
    return result, counter, time_counter


def save_report(data, file_name, save_dir, is_json):
    file_type = 'json' if is_json else 'html'
    full_file_name = '{}.{}'.format(file_name, file_type)
    if not is_json:
        with open('report.html', 'rb') as f:
            template = f.read()
            with open(save_dir + '/' + full_file_name, 'wb') as wf:
                wf.write(template.replace('$table_json', data))
    else:
        with open(save_dir + '/' + full_file_name, 'wb') as wf:
            wf.write(data)
    print 'Report has been created: {}'.format(full_file_name)


def main():
    args = parse_args()

    log_dir = config['LOG_DIR']
    if not args.log_path:
        last_log_date, last_log_path = get_last_log(log_dir)
    else:
        last_log_path = args.log_path
        last_log_date = re.findall('\d+', last_log_path)[0]

    report_dir = config['REPORT_DIR']
    report_name_date = '.'.join([last_log_date[:4], last_log_date[4:6], last_log_date[-2:]])
    report_name = 'report-' + report_name_date

    if exists_last_report(report_name, report_dir):
        print 'Latest report already exists: {}'.format(report_name)
        return None

    if '.gz' in last_log_path:
        with gzip.open(last_log_path, 'rb') as f:
            csv_reader = csv.reader(f)
            base_report, total_count, total_time = log_parser(csv_reader)
    else:
        with open(last_log_path, 'rb') as f:
            csv_reader = csv.reader(f)
            base_report, total_count, total_time = log_parser(csv_reader)

    report = []
    for i in base_report:
        url = i
        count = len(base_report[i])
        count_perc = round(1.0 * count / total_count, 5)
        time_sum = round(sum(base_report[i]), 5)
        time_max = round(max(base_report[i]), 5)
        time_perc = round(1.0 * time_sum / total_time, 5)
        time_p50 = round(np.percentile(np.array(base_report[i]), 50), 5)
        time_p95 = round(np.percentile(np.array(base_report[i]), 95), 5)
        time_p99 = round(np.percentile(np.array(base_report[i]), 99), 5)
        entry = {
            'url': url,
            'count': count,
            'count_perc': count_perc,
            'time_sum': time_sum,
            'time_max': time_max,
            'time_perc': time_perc,
            'time_p50': time_p50,
            'time_p95': time_p95,
            'time_p99': time_p99
        }

        report.append(entry)

    report_sorted = sorted(
        report,
        key=lambda k: k['time_max'],
        reverse=True
    )[:config['REPORT_SIZE'] + 1]
    report_str = json.dumps(report_sorted)

    save_report(report_str, report_name, report_dir, args.json)


if __name__ == "__main__":
    main()
