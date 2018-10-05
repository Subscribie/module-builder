#!/usr/bin/env python
import sqlite3
import argparse


def up():
    con = sqlite3.connect(args.db)

    cur = con.cursor()
    cur.executescript('''
	CREATE TABLE  IF NOT EXISTS onboard_item 
	(                                
	name text,                                                           
	complete boolean default 0                                     
	);
        INSERT INTO onboard_item (name) VALUES("has_connected_stripe"); 
        INSERT INTO onboard_item (name) VALUES("has_connected_gocardless"); 
    ''')
    con.commit()

def down():
    con = sqlite3.connect(args.db)
    cur = con.cursor()
    cur.execute('''
        DROP TABLE onboard_item
    ''')
    con.commit()

parser = argparse.ArgumentParser()
parser.add_argument("-db", "-database", default="../../../data.db", help="Path to the sqlite database")
group = parser.add_mutually_exclusive_group()
group.add_argument("-up", action="store_true", help="Run the 'up' migration.")
group.add_argument("-down", action="store_true", help="Run the 'down' migration.")

args = parser.parse_args()

if args.up:
    print("Running 'up' migration.")
    up()
elif args.down:
    print("Running 'down' migration.")
    down()
