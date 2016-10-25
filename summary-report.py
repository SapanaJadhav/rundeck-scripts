#!/usr/bin/env python
"""
    Script to parse Rundeck execution log and
    send a summary email with all job failures

    This script uses pygtail to tail logs
    Run this script as a cron at whatever interval you desire
    (the mail text is written expecting 3 hour interval, you can edit that)
"""

##########
# User editable variables BEGIN
##########

# Name of the Rundeck project for which you want reports, usually Production
PROJECT = "Production"

# Recipients for the summary email
rcv = ['team-devops@domain.com', 'team-devs@domain.com']

# SMTP server to send mails from
smtp_server = 'mail.domain.com'

# SMTP authentication username, also the data-from user for email, ie. what the recipient sees in an email client
smtp_username = 'system-reports@domain.com'

# SMTP authentication password
smtp_password = 'goodstrongpassword'

# Set default SMTP port
smtp_port = 587

# This will be used in the job execution links in summary email, this can be IP or hostname
BASE_URL = "https://rundeck.internal.domain.tld"

##########
# User editable variables END
##########

#To the arguments handling
import sys
import getopt

import socket
from pygtail import Pygtail
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
  opts, args = getopt.getopt(sys.argv[1:],"hh:p:f:t:s:b:g:",["help="])
except getopt.GetoptError:
  print 'Try to use the help with the following command: summary-report.py -h'
  sys.exit(2)

for opt,arg in opts:
  if opt == '-h':
    print """summary-report.py has the following arguments options:
      -p <production>
      -t <recipients emails>
      -s <smtp host/sender email>
      -b <base url>
    """
    sys.exit()
  elif opt == "-p":
    PROJECT = arg
  elif opt == "-t":
    rcv = arg
  elif opt == "-s":
    smtp_username = arg
  elif opt == "-b":
    BASE_URL = arg
  elif opt == "-g":
    try:
      smtp_port = int(arg)
    except ValueError:
      print("Option '-g' needs an integer as argument.")
      sys.exit()

LOG = "/var/log/rundeck/rundeck.executions.log"
fail_count = 0

msg = MIMEMultipart('alternative')
msg['From'] = smtp_username
msg['To'] = ", ".join(rcv)

jobs = ''

for line in Pygtail(LOG):
  status = line.split()[4]

  # Look for jobs that failed after retries, or timed out
  # This will exclude jobs that succeed after a retry
  if any(err_msg in status for err_msg in ("failed]", "timedout]")):
    fail_count += 1
    date = line.split()[0].strip("[") + " " + line.split()[1].strip("]").split(",")[0]
    job_name = " ".join(line.split()[7:]).split("\"")[1].strip("-/")
    execution_id = status.split(":")[0].strip("[")
    link = BASE_URL + "/project/" + PROJECT + "/execution/show/" + execution_id
    jobs += date + " &nbsp; &nbsp; &nbsp; " + '<a href=' + link + '>' + execution_id + '</a>' + " &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; " + job_name + "<br/>"

if jobs:
  mail_text = "List of jobs that failed in the last 3 hours (click on the execution ID below to view details of the failed job):<br/>" + '<p><strong>Time &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; Execution ID &nbsp; &nbsp; &nbsp; Job name</strong></p>' + jobs

# Send mail only if there are failures;
# Remove this if conditional to send mail always
if fail_count > 0:
  msg['Subject'] = 'Rundeck summary: ' + str(fail_count) + ' jobs failed'
  part1 = MIMEText(mail_text, 'plain')
  part2 = MIMEText(mail_text, 'html')
  msg.attach(part1)
  msg.attach(part2)

  server = smtplib.SMTP(smtp_server, smtp_port)
  server.starttls()
  server.login(smtp_username, smtp_password)
  server.sendmail(smtp_username, rcv, msg.as_string())
  server.quit()
