#
# Copyright (C) 2015 INRA
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import cherrypy
import argparse
import textwrap
import string
import json
import os


WEB_DIR = os.path.abspath(os.path.join(__file__, "../../docs"))

class AppServer(object):
    
    OUTPUT_DIRECTORY = "/tmp"
    
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("/app/index.html")

    @cherrypy.expose
    def process_venn(self, **kwargs):
        delimiter = '\t'
        if (kwargs["delimiter"] == "," or kwargs["delimiter"] == ";") :
           delimiter = kwargs["delimiter"]
        try:
            file_path = self.__upload(**kwargs)
        except:
            return json.dumps([{'error':"Error: Please provide a delimited text file."}])
        return self.__compare_lists(file_path, kwargs["header"], delimiter)

    def __upload(self, **kwargs):

        # the file transfer can take a long time; by default cherrypy
        # limits responses to 300s; we increase it to 1h
        cherrypy.response.timeout = 3600
        
        # upload file by chunks
        filepath = os.path.join(self.OUTPUT_DIRECTORY, kwargs["browse_upload"].filename)
        FH_sever_file = open(filepath, "w")
        while True:
            data = kwargs["browse_upload"].file.read(8192)
            if not data:
                break
            if isinstance(data, bytes):
                FH_sever_file.write(data.decode())
            else:
                FH_sever_file.write(data)
        FH_sever_file.close()
        
        return(filepath)

    def __compare_lists ( self, file, header, spliter):
        
        FH = open(file,'r')
        names = {}
        samples = {}
        fieldnb = 0
        
        for i, line in enumerate(FH.readlines()):
            if i == 0:
                fieldnb = len(line.split(spliter))
            if i == 0 and header:
                for j, val in enumerate(line.split(spliter)):
                    names[string.ascii_uppercase[j]] = val.rstrip('\n\r')
                fieldnb = len(names)
            else:
                for j, val in enumerate(line.split(spliter)):
                    if i == 0:
                        names[string.ascii_uppercase[j]] = "List " + str(j+1)
                    if j in samples:
                        samples[j].append(val)
                    else:
                        samples[j] = [val]  
                if fieldnb < len(line.split(spliter)):
                    return json.dumps([{'error':"Error: Inconsistent number of fields line " + str(i+1) + 
                                        " (" + str(len(line.split(spliter))) + " for " + str(fieldnb) + " expected)"}])
                    
        d = {}
        j = 1
        
        if len(names)>6:
            return json.dumps([{'error':"Error: too many columns (" + str(len(names)) + ">6) in input file!"}])
        
        for s in samples:
            for line in samples[s]:
                if line.rstrip('\n\r') in d:
                    #already view in the current file (duplicate) ?
                    if d[line.rstrip('\n\r')] - j < 0:
                        d[line.rstrip('\n\r')] += j
                else:
                    if line.rstrip('\n\r') != "":
                        d[line.rstrip('\n\r')] = j
            j *= 10
    
        d2 = {}
        for key, val in d.items():
            if str(val).zfill(len(samples)) in d2:
                d2[str(val).zfill(len(samples))].append(key)
            else:
                d2[str(val).zfill(len(samples))] = [key]
    
        values = {}
        data = {}
        for key in sorted(d2):
            k = ""
            for i in range(len(key)):
                if key[len(key)-(i+1)] == "1":
                    k = k + string.ascii_uppercase[i]
            values[k] = len(d2[key])
            data[k] = []
            data[k].append('\n'.join(d2[key]))
        return json.dumps([{'name': names, 'values' : values, 'data':data}], indent=4, sort_keys=True)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true", dest="daemon", default=False, help="Run the server as daemon")
    args = vars(parser.parse_args())

    if args["daemon"]:
        from cherrypy.process.plugins import Daemonizer
        Daemonizer(cherrypy.engine).subscribe()

    app_conf = {
        '/':
            {'tools.staticdir.root': WEB_DIR},
        os.path.join('/', 'css'):
            {'tools.staticdir.on'  : True, 'tools.staticdir.dir' : './css/'},
        os.path.join('/', 'js'):
            {'tools.staticdir.on'  : True, 'tools.staticdir.dir' : './js/'},
        os.path.join('/', 'img'):
            {'tools.staticdir.on'  : True, 'tools.staticdir.dir' : './img/'},
        os.path.join('/', 'app'):
            {'tools.staticdir.on'  : True, 'tools.staticdir.dir' : './'}
    }
    
    cherrypy.quickstart(AppServer(), config=app_conf)
     