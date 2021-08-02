from flask import Blueprint, render_template, redirect, send_from_directory
from flask import current_app as app
from pathlib import Path
import functools
import json

from flask.helpers import make_response

import jimi

from plugins.packageDeployer.models import packageDeployer
from plugins.asset.models import asset
from plugins.playbook.models import playbook

pluginPages = Blueprint('packageDeployerPages', __name__, template_folder="templates")

# SEC #
# * PUBLIC should be replaced with @publicEndpoint - need to build  

def authenticated(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            if jimi.auth.validateSession(jimi.api.request.cookies["packageDeployer"],"packageDeployer"):
                return f(*args, **kwargs)
        except Exception as e:
            pass
        return "Authentication Required", 403
    return wrap

@pluginPages.route('/includes/<file>')
def __PUBLIC__custom_static(file):
    return send_from_directory(str(Path("plugins/packageDeployer/web/includes")), file)

@pluginPages.route("/",methods=["GET"])
def __PUBLIC__mainPage():
    domainList = [x for x in jimi.settings.getSetting("ldap",None)["domains"]]
    domains = {"default" : domainList[0]["name"], "additional" : [x["name"] for x in domainList[1:]]}
    return render_template("userLogin.html", domains=domains)

@pluginPages.route("/",methods=["POST"])
def __PUBLIC__doLogin():
    data = json.loads(jimi.api.request.data)
    if data["domain"] == "local":
        userSession = jimi.auth.validateUser(data["username"],data["password"])
    else:
        userSession = jimi.auth.validateExternalUser(data["username"],data["password"],"ldap",domain=data["domain"],application="packageDeployer")
    if userSession is not None:
        response = make_response({}, 200)
        response.set_cookie("packageDeployer", value=userSession, max_age=1800, httponly=False)
    else:
        response = make_response({ "msg": "Incorrect credentials" },403)
    
    return response

@pluginPages.route("/devices/",methods=["GET"])
@authenticated
def __PUBLIC__devices():
    sessionData = jimi.auth.validateSession(jimi.api.request.cookies["packageDeployer"],"packageDeployer",False)["sessionData"]
    devices = asset._asset().query(query={ "assetType" : "computer", "fields.user" : sessionData["user"] },fields=["name"])["results"]
    result = []
    for device in devices:
        result.append({"_id" : device["_id"], "name" : device["name"]})
    return { "results" : result }, 200

@pluginPages.route("/device/<asset_id>/",methods=["GET"])
@authenticated
def __PUBLIC__manageDevicePage(asset_id):
    packages = __PUBLIC__packages(asset_id)[0]["results"]
    containers = packageDeployer._packageDeployer().query(query={ "container" : True })["results"]
    device = asset._asset().query(id=asset_id)["results"][0]["name"]
    return render_template("packages.html", packages=packages, device=device, containers=containers)

@pluginPages.route("/device/<asset_id>/packages/",methods=["GET"])
@authenticated
def __PUBLIC__packages(asset_id):
    packages = packageDeployer._packageDeployer().query(query={"$or":[{"container_name":""},{"container_name":{"$exists":False}}]})["results"]
    playbookNames = []
    for package in packages:
        try:
            #if 
            playbookNames.append(package["playbook_name"])
        except:
            pass
    playbooks = playbook._playbook().query(query={ "name" : { "$in" : playbookNames }, "playbookData.asset_id" : asset_id },fields=["_id","playbookData","result","name"])["results"]
    playbookHash = {}
    for playbookItem in playbooks:
        playbookHash[playbookItem["name"]] = playbookItem
    for package in packages:
        if package["playbook_name"] in playbookHash:
            if playbookHash[package["playbook_name"]]["result"]:
                package["status"] = "Installed"
            else:
                try:
                    package["status"] = playbookHash[package["playbook_name"]]["playbookData"]["status"]
                except KeyError:
                    package["status"] = "Unknown"
        else:
            package["status"] = "Available"
    return { "results" : packages }, 200

@pluginPages.route("/device/<asset_id>/<container_id>/",methods=["GET"])
@authenticated
def __PUBLIC__manageDeviceContainerPage(asset_id,container_id):
    packages = __PUBLIC__containerPackages(asset_id,container_id)[0]["results"]
    device = asset._asset().query(id=asset_id)["results"][0]["name"]
    return render_template("packages.html", packages=packages, device=device, containers=[])

@pluginPages.route("/device/<asset_id>/<container_id>/packages/",methods=["GET"])
@authenticated
def __PUBLIC__containerPackages(asset_id,container_id):
    container = packageDeployer._packageDeployer().query(id=container_id)["results"][0]
    packages = packageDeployer._packageDeployer().query(query={ "container_name" : container["name"], "container" : { "$ne" : True } })["results"]
    playbookNames = []
    for package in packages:
        try:
            playbookNames.append(package["playbook_name"])
        except:
            pass
    playbooks = playbook._playbook().query(query={ "name" : { "$in" : playbookNames }, "playbookData.asset_id" : asset_id },fields=["_id","playbookData","result","name"])["results"]
    playbookHash = {}
    for playbookItem in playbooks:
        playbookHash[playbookItem["name"]] = playbookItem
    for package in packages:
        if package["playbook_name"] in playbookHash:
            if playbookHash[package["playbook_name"]]["result"]:
                package["status"] = "Installed"
            else:
                try:
                    package["status"] = playbookHash[package["playbook_name"]]["playbookData"]["status"]
                except KeyError:
                    package["status"] = "Unknown"
        else:
            package["status"] = "Available"
    return { "results" : packages }, 200

@pluginPages.route("/device/<asset_id>/<container_id>/package/<package_id>/",methods=["GET"])
@authenticated
def __PUBLIC__Containerpackage(asset_id,container_id,package_id):
    return __PUBLIC__package(asset_id,package_id)

@pluginPages.route("/device/<asset_id>/package/<package_id>/",methods=["GET"])
@authenticated
def __PUBLIC__package(asset_id,package_id):
    package = packageDeployer._packageDeployer().query(id=package_id)["results"][0]
    try:
        playbookPackage = playbook._playbook().query(query={ "name" : package["playbook_name"], "playbookData.asset_id" : asset_id },fields=["_id","playbookData","result","name"])["results"][0]
        package["status"] = "Available"
        if playbookPackage["result"]:
            package["status"] = "Installed"
        else:
            try:
                package["status"] = playbookPackage["playbookData"]["status"]
            except KeyError:
                package["status"] = "Unknown"
    except:
        package["status"] = "Available"
    return package, 200

@pluginPages.route("/device/<asset_id>/<container_id>/deploy/<package_id>/",methods=["GET"])
@authenticated
def __PUBLIC__containerDeployPackage(asset_id,container_id,package_id):
    return __PUBLIC__deployPackage(asset_id,package_id)

@pluginPages.route("/device/<asset_id>/deploy/<package_id>/",methods=["GET"])
@authenticated
def __PUBLIC__deployPackage(asset_id,package_id):
    package = packageDeployer._packageDeployer().query(id=package_id)["results"][0]
    playbookPackage = playbook._playbook().query(query={ "name" : package["playbook_name"], "playbookData.asset_id" : asset_id },fields=["_id","name","playbookData","result","name"])["results"]
    if len(playbookPackage) == 0:
        playbook._playbook().new(package["acl"],package["playbook_name"],asset_id,{ "asset_id" : asset_id, "status" : "Requested" },0,0)
        return { }, 200
    return { }, 404
