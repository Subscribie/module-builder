#!/usr/bin/env python
import sqlite3
import argparse

def up():
  con = sqlite3.connect(args.db)
  cur = con.cursor()
  cur.executescript('''
    CREATE TABLE IF NOT EXISTS builder_sites 
    (
      site_url text,
      email text
    );
  ''')
  con.commit()

def down():
  con = sqlite3.connect(args.db)
  cur = con.cursor()
  cur.executescript('''
    DROP TABLE builder_sites
  ''')
  con.commit()

parser = argparse.ArgumentParser()
parser.add_argument("-db", "-database", default="./data.db", help="Path to the sqlite database")
group = parser.add_mutually_exclusive_group()
group.add_argument("-up", action="store_true", help="Run the 'up' migration.")
group.add_argument("-down", action="store_true", help="Run the 'down' migration.")

args = parser.parse_args()

if args.up:
  print("Running up migration")
  up()

if args.down:
  print("Running down migration")
  down()
