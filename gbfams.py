﻿from urllib.request import urlopen
from urllib import request, parse
from urllib.parse import unquote
import os
import sys
import json
import csv
import concurrent.futures
from threading import Thread, Lock
from queue import Queue
import time
import pyperclip

class Task():
    def __init__(self, parent, key, start, count, use_db, dupe, save, silent):
        self.parent = parent
        self.lock = Lock()
        self.id = start
        self.errc = 0
        self.max_thread = 8
        self.key = key
        self.rsc = self.parent.rsc[key]
        self.count = count
        self.running = True
        self.max_id = self.rsc.get("max_id", -1)
        self.use_db = use_db
        self.dupe = dupe
        self.silent = silent
        self.save = save
        self.urls = []
        self.pause = False

    def run(self):
        if self.key not in self.parent.data:
            self.parent.data[self.key] = []
            self.parent.savePending = True
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_thread) as executor:
            futures = [executor.submit(self.worker) for i in range(self.max_thread)]
            try:
                for future in concurrent.futures.as_completed(futures):
                    future.result()
            except KeyboardInterrupt:
                print("Forced stop")
                self.running = False
        print(self.rsc["name"], ":", len(self.urls), "positive result(s)")
        return self.urls

    def worker(self):
        while self.running:
            with self.lock:
                if not self.running: return
                id = self.id
                self.id += 1
                if self.count > 0:
                    self.count -= 1
                    if self.count == 0:
                        self.running = False
                if self.max_id != -1 and self.id > self.max_id:
                    return
                if self.dupe and id in self.parent.data[self.key]:
                    continue

            found = False
            for im in self.rsc["images"]:
                for path in im["path"]:
                    for prefix in im["prefix"]:
                        for suffix in im["suffix"]:
                            url = self.parent.endpoint + self.parent.lang[self.parent.settings['lang']] + self.parent.quality[self.parent.settings['quality']] + path
                            file = prefix
                            if "zfill" in self.rsc: file += str(id).zfill(self.rsc["zfill"])
                            else: file += str(id)
                            file += suffix
                            try:
                                url_handle = self.parent.request(url + file)
                                data = url_handle.read()
                                url_handle.info()['Last-Modified']
                                try:
                                    if not self.save or len(data) <= 200 or not self.parent.folderCheck(self.key): raise Exception()
                                    with open(self.key + "/" + file, "wb") as f:
                                        f.write(data)
                                except:
                                    pass
                                found = True
                                with self.lock:
                                    if self.use_db and id not in self.parent.data[self.key]:
                                        self.parent.data[self.key].append(id)
                                        self.parent.savePending = True
                                    if not self.silent: print("#"+str(len(self.urls))+":", file, "found")
                                    self.urls.append(url + file)
                                    self.errc = 0
                            except:
                                with self.lock:
                                    if im is self.rsc["images"][-1] and path is im["path"][-1] and prefix is im["prefix"][-1] and suffix is im["suffix"][-1]:
                                        self.errc += 1
                                        if self.errc >= self.rsc.get("max_err", 40):
                                            self.running = False
                            if found: break
                        if found: break
                    if found: break
                if found: break


class Datamine():
    def __init__(self):
        try:
            with open('data.json') as f:
                self.data = json.load(f)
        except:
            self.data = {}
        self.endpoint = "http://game-a.granbluefantasy.jp/"
        self.lang = ["assets/", "assets_en/"]
        self.quality = ["img_low/", "img_mid/", "img/"]
        self.rsc = {
            'ssrchar' : {
                "name": "SSR Character",
                "max_id" : 9999,
                "zfill" : 4,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/npc/zoom/"],
                        "prefix": ["304", "374", "384"],
                        "suffix": ["000_01.png"]
                    }
                ]
            },
            'srchar' : {
                "name": "SR Character",
                "max_id" : 9999,
                "zfill" : 4,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/npc/zoom/"],
                        "prefix": ["303", "373", "383"],
                        "suffix": ["000_01.png"]
                    }
                ]
            },
            'rchar' : {
                "name": "R Character",
                "max_id" : 9999,
                "zfill" : 4,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/npc/zoom/"],
                        "prefix": ["302", "372", "382"],
                        "suffix": ["000_01.png"]
                    }
                ]
            },
            'skin' : {
                "name": "Character Skin",
                "max_id" : 9999,
                "zfill" : 4,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/npc/zoom/"],
                        "prefix": ["371"],
                        "suffix": ["000_01.png"]
                    }
                ]
            },
            'ssrsumn' : {
                "name": "SSR Summon",
                "max_id" : 9999,
                "zfill" : 4,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/summon/b/"],
                        "prefix": ["204"],
                        "suffix": ["000.png", "000_01.png"]
                    }
                ]
            },
            'srsumn' : {
                "name": "SR Summon",
                "max_id" : 9999,
                "zfill" : 4,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/summon/b/"],
                        "prefix": ["203"],
                        "suffix": ["000.png"]
                    }
                ]
            },
            'rsumn' : {
                "name": "R Summon",
                "max_id" : 9999,
                "zfill" : 4,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/summon/b/"],
                        "prefix": ["202"],
                        "suffix": ["000.png"]
                    }
                ]
            },
            'npc' : {
                "name": "NPC",
                "max_id" : 9999,
                "zfill" : 4,
                "max_err": 30,
                "images": [
                    {
                        "path": ["sp/quest/scene/character/body/"],
                        "prefix": ["399"],
                        "suffix": ["000.png"]
                    }
                ]
            },
            'skill' : {
                "name": "Skill",
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/ui/icon/ability/m/"],
                        "prefix": [""],
                        "suffix": ["_1.png", "_2.png", "_3.png", "_4.png", "_5.png", ]
                    }
                ]
            },
            'icon0' : {
                "name": "Buff Icon 0000",
                "max_err": 50,
                "min_id": 0,
                "max_id": 999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'icon1' : {
                "name": "Buff Icon 1000",
                "max_err": 50,
                "min_id": 1000,
                "max_id": 1999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'icon2' : {
                "name": "Buff Icon 2000",
                "max_err": 50,
                "min_id": 2000,
                "max_id": 2999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'icon3' : {
                "name": "Buff Icon 3000",
                "max_err": 50,
                "min_id": 3000,
                "max_id": 3999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'icon4' : {
                "name": "Buff Icon 4000",
                "max_err": 50,
                "min_id": 4000,
                "max_id": 4999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'icon5' : {
                "name": "Buff Icon 5000",
                "max_err": 50,
                "min_id": 5000,
                "max_id": 5999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'icon6' : {
                "name": "Buff Icon 6000",
                "max_err": 50,
                "min_id": 6000,
                "max_id": 6999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'icon7' : {
                "name": "Buff Icon 7000",
                "max_err": 50,
                "min_id": 7000,
                "max_id": 7999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'icon8' : {
                "name": "Buff Icon 8000",
                "max_err": 50,
                "min_id": 8000,
                "max_id": 8999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'icon9' : {
                "name": "Buff Icon 9000",
                "max_err": 50,
                "min_id": 9000,
                "max_id": 9999,
                "images": [
                    {
                        "path": ["sp/ui/icon/status/x64/status_"],
                        "prefix": [""],
                        "suffix": [".png"]
                    }
                ]
            },
            'enemy62' : {
                "name": "Enemy #62",
                "max_err": 40,
                "max_id": 9999,
                "zfill": 4,
                "images": [
                    {
                        "path": ["sp/assets/enemy/s/"],
                        "prefix": ["62"],
                        "suffix": ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "7.png", "8.png", "9.png"]
                    },
                    {
                        "path": ["sp/cjs/raid_appear_"],
                        "prefix": ["62"],
                        "suffix": ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "7.png", "8.png", "9.png"]
                    }
                ]
            },
            'enemy81' : {
                "name": "Enemy #81",
                "max_err": 40,
                "max_id": 9999,
                "zfill": 4,
                "images": [
                    {
                        "path": ["sp/assets/enemy/s/"],
                        "prefix": ["81"],
                        "suffix": ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "7.png", "8.png", "9.png"]
                    },
                    {
                        "path": ["sp/cjs/raid_appear_"],
                        "prefix": ["81"],
                        "suffix": ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "7.png", "8.png", "9.png"]
                    }
                ]
            },
            'enemy91' : {
                "name": "Enemy #91",
                "max_err": 40,
                "max_id": 9999,
                "zfill": 4,
                "images": [
                    {
                        "path": ["sp/assets/enemy/s/"],
                        "prefix": ["91"],
                        "suffix": ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "7.png", "8.png", "9.png"]
                    },
                    {
                        "path": ["sp/cjs/raid_appear_"],
                        "prefix": ["91"],
                        "suffix": ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "7.png", "8.png", "9.png"]
                    }
                ]
            },
            'ticket' : {
                "name": "Draw Ticket",
                "max_id": 9999,
                "zfill" : 4,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/item/ticket/"],
                        "prefix": ["1"],
                        "suffix": ["1.jpg"]
                    }
                ]
            },
            'sword' : {
                "name": "SSR Sword",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10400"],
                        "suffix": ["00.jpg"]
                    }
                ]
            },
            'dagger' : {
                "name": "SSR Dagger",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10401"],
                        "suffix": ["00.jpg"]
                    }
                ]
            },
            'spear' : {
                "name": "SSR Spear",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10402"],
                        "suffix": ["00.jpg"]
                    }
                ]
            },
            'axe' : {
                "name": "SSR Axe",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10403"],
                        "suffix": ["00.jpg"]
                    }
                ]
            },
            'staff' : {
                "name": "SSR Staff",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10404"],
                        "suffix": ["00.jpg"]
                    }
                ]
            },
            'gun' : {
                "name": "SSR Gun",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10405"],
                        "suffix": ["00.jpg"]
                    }
                ]
            },
            'melee' : {
                "name": "SSR Melee",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10406"],
                        "suffix": ["00.jpg"]
                    }
                ]
            },
            'bow' : {
                "name": "SSR Bow",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10407"],
                        "suffix": ["00.jpg"]
                    }
                ]
            },
            'harp' : {
                "name": "SSR Harp",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10408"],
                        "suffix": ["00.jpg"]
                    }
                ]
            },
            'katana' : {
                "name": "SSR Katana",
                "max_id": 999,
                "zfill" : 3,
                "max_err": 40,
                "images": [
                    {
                        "path": ["sp/assets/weapon/m/"],
                        "prefix": ["10409"],
                        "suffix": ["00.jpg"]
                    }
                ]
            }
        }
        self.savePending = False
        self.settings = {
            "lang": 1,
            "quality": 0,
            "proxy": "",
            "forceproxy": False
        }
        self.hasProxy = False
        self.running = False

    # called once at the start
    def load(self):
        try:
            with open('setting.json') as f:
                self.settings = {**self.settings, **(json.load(f))}
                return True
        except Exception as e:
            print("Failed to load settings.json, a new one will be created")
            print('Exception:', e)
            return False

    # called once at the end
    def save(self):
        try:
            with open('setting.json', 'w') as outfile:
                json.dump(self.settings, outfile)
            return True
        except Exception as e:
            print("Failed to save settings.json")
            print('Exception:', e)
            return False
            
    # called once at the end
    def saveData(self):
        if not self.savePending: return True
        try:
            with open('data.json', 'w') as outfile:
                json.dump(self.data, outfile)
            print("data.json updated")
            return True
        except Exception as e:
            print("Failed to save data.json")
            print('Exception:', e)
            return False

    def askQuestion(self, question):
        while True:
            anwser = input(question)
            if anwser == "y" or anwser == "Y":
                return True
            if anwser == "n" or anwser == "N":
                return False
                break
            print("Please respond with 'y' for Yes or 'n' for No")

    def askNumber(self, question, min, max=-1):
        while True:
            count = input(question)
            if count.isdigit() and int(count) >= min and ((max != -1 and int(count) <= max) or max == -1):
                return int(count)
            else:
                print("Please input a number (valid range: " + str(min) + "-" + str(max) + ")")

    # for the main menu
    def menu(self, question, choices, verify): # return the user string. If verify is true, it has to be a valid choice
        print(question)
        for c in choices:
            print("[" + c[0] + "] " + c[1])
        while True:
            ch = input()
            if not verify:
                return ch
            for c in choices:
                if c[0] == ch:
                    return ch
            print("Invalid choice, try again: ")

    # check if a folder exists
    def folderCheck(self, folder): # return true if the folder exists, false if it doesn't AND if we failed to create one
        if not os.path.exists(folder):
            try:
                os.makedirs(folder) # if not, create
            except OSError as e:
                return False
        return True

    def manual(self):
        choices = []
        table = []
        for k in self.rsc:
            choices.append([str(len(choices)), self.rsc[k]['name']])
            table.append(k)
        choices.append(["Any Key", "Back"])
        while True:
            s = self.menu("\nWhat to mine?", choices, False)
            try:
                rsc = self.rsc[table[int(s)]]
                start = self.askNumber("Input the starting ID: ", rsc.get("min_id", 0), rsc.get("max_id", -1))
                count = self.askNumber("How many elements: ", 0, rsc.get("max_id", -1))
                use_db = self.askQuestion("Update data.json? (y/n): ")
                dupe = self.askQuestion("Ignore know elements from data.json? (y/n): ")
                saving = self.askQuestion("Save assets on disk? (y/n): ")
                task = Task(self, table[int(s)], start, count, use_db, dupe, saving, False)
                results = task.run()
                if len(results) > 0 and self.askQuestion("Copy " + results[0] + " to the clipboard? (y/n): "):
                    if len(results) > 1:
                        while True:
                            key = self.askNumber("Input a key (range 0-" + str(len(results)-1) + "): ", 0, len(results)-1)
                            pyperclip.copy(results[key])
                            if not self.askQuestion("URL has been copied to your clipboard, continue? (y/n): "):
                                break
                    else:
                        pyperclip.copy(results[0])
                        print("URL has been copied to your clipboard")
            except Exception as e:
                print(e)
            break

    def auto(self):
        options = {}
        table = []
        for k in self.rsc:
            options[k] = False
            table.append(k)
        while True:
            choices = []
            for k in self.rsc:
                choices.append([str(len(choices)), "[{}] ".format("X" if options[k] else " ") + self.rsc[k]['name']])
            choices += [["S", "Select All"], ["C", "Cancel All"], ["M", "Start mining"], ["Any Key", "Back"]]
            s = self.menu("\nWhat to mine?", choices, False)
            try:
                options[table[int(s)]] = not options[table[int(s)]]
            except:
                if s.lower() == "s":
                    for k in options: options[k] = True
                elif s.lower() == "c":
                    for k in options: options[k] = False
                elif s.lower() == "m":
                    tasks = {}
                    for k in options:
                        if options[k]:
                            if k in self.data and len(self.data[k]) > 0: start = self.data[k][-1]
                            else: start = self.rsc[k].get("min_id", 0)
                            start = max(0, start-10)
                            tasks[k] = Task(self, k, start, -1, True, True, True, True)
                    if len(tasks) == 0:
                        print("Please select what to mine")
                    else:
                        print("Starting mining...")
                        with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
                            futures = [executor.submit(tasks[k].run) for k in tasks]
                            for future in concurrent.futures.as_completed(futures):
                                future.result()
                else:
                    return

    def modifySettings(self):
        while True:
            s = self.menu("\nSetting menu", [["0", "Toggle Asset Language (Current: " + ("JP" if self.settings["lang"] == 0 else "EN") + ")"], ["1", "Change Asset Quality (Current: " + ("Low" if self.settings["quality"] == 0 else ("Mid" if self.settings["quality"] == 1 else "High")) + ")"], ["2", "Set a Proxy"], ["3", "Toggle the Proxy Check (Current: " + self.getProxy() + ")"], ["Any Key", "Back"]], False)
            if s == "0":
                if self.settings['lang'] == 0: self.settings['lang'] = 1
                else: self.settings['lang'] = 0
                self.save()
            elif s == "1":
                self.settings['quality'] = (self.settings['quality'] + 1) % 3
                self.save()
            elif s == "2":
                self.inputProxy()
                self.save()
            elif s == "3":
                self.settings['forceproxy'] = not self.settings['forceproxy']
                self.save()
            else:
                return

    # main loop
    def loop(self):
        # MAIN MENU
        while True:
            s = self.menu("\nMain menu", [["0", "Manual"], ["1", "Auto"], ["2", "Settings"], ["Any Key", "Exit"]], False)
            # SUB MENU ################################################################
            if s == "0":
                if not self.hasProxy:
                    if self.settings['forceproxy']:
                        print("\nPlease set a proxy before continuing")
                        input("Press return to go back to the main Menu")
                        continue
                    print("\nWarning: No proxy set!!!")
                self.manual()
                self.saveData()
            elif s == "1":
                if not self.hasProxy:
                    if self.settings['forceproxy']:
                        print("\nPlease set a proxy before continuing")
                        input("Press return to go back to the main Menu")
                        continue
                    print("\nWarning: No proxy set!!!")
                self.auto()
                self.saveData()
            elif s == "2":
                self.modifySettings()
            else: # quit
                return

    def start(self):
        # we start HERE
        print("GBF Asset Mining Script v1.0")

        self.load() # load the settings
        print("Proxy check...")
        if self.checkProxy(self.settings['proxy']) != 0:
            print("Warning: Invalid or no proxy set")
        else:
            print("Done")
            self.hasProxy = True
        while self.loop(): # loop as long as loop() returns true
            pass
        self.save() # save the settings

    def request(self, url):
        if self.hasProxy:
            prx = request.ProxyHandler({'http': self.settings['proxy']})
            opener = request.build_opener(prx)
            req = request.Request(url)
            return opener.open(req)
        else:
            req = request.Request(url)
            return request.urlopen(req)

    # proxy check
    def checkProxy(self, purl):
        try: # set the proxy
            prx = request.ProxyHandler({'http': purl})
            opener = request.build_opener(prx)
        except:
            return 1 # wrong, return 1
        try:
            req = request.Request('http://game.granbluefantasy.jp') # test to get google.com
            url_handle = opener.open(req, timeout=10)
        except:
            return 2 # wrong, return 2
        try:
            req = request.Request('http://game-a1.granbluefantasy.jp/assets_en/img/sp/assets/npc/m/3040000000_01.jpg') # test to get gawain
            req.add_header('Referer', 'http://game.granbluefantasy.jp/')
            url_handle = opener.open(req, timeout=10)
        except:
            return 3 # wrong, return 3
        return 0 # we are good

    # proxy change
    def inputProxy(self):
        p = input("Input the proxy IP you want to use (leave blank to cancel): ")
        if len(p) == 0:
            return 0 # empty, we do nothing

        # special commands
        if p == "delete":
            print("Deleted")
            self.hasProxy = False
            self.settings['proxy'] = ""
            return 0
        elif p == "disable":
            print("Disabled")
            hasProxy = False
            return 0
        elif p == "enable":
            if checkProxy(self.settings['proxy']) == 0:
                print("Enabled")
                self.hasProxy = True
            else:
                print("Can't use the current proxy")
            return 0

        # check new proxy
        print("Checking...")
        r = self.checkProxy(p)
        if r == 0:
            self.settings['proxy'] = p
            print("New Proxy set to", self.settings['proxy'])
            self.hasProxy = True
            return 1 # 1 means we successfully changed the proxy
        elif r == 1:
            print("Invalid Proxy")
        elif r == 2:
            print("Proxy error")
        elif r == 3:
            print("Proxy might be banned or GBF is down")
        return 2 # 2 means error

    # return the proxy in stream format or "Disabled" if disabled
    def getProxy(self):
        if not self.hasProxy:
            return "Disabled"
        return self.settings['proxy']

if __name__ == '__main__':
    d = Datamine()
    d.start()