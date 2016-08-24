import sys
import os
import subprocess
import re
from os import listdir
from os.path import isfile, join
import urllib


BASE_DIR = os.getcwd()
SVN_BASE 	= "https://ps-svn.aws.marketlive.com/marketlive/"
SITES 		= "sites/"
MARKETLIVE_HOME = os.environ["MARKETLIVE_HOME"]
TOMCAT_SCRIPTS 	= MARKETLIVE_HOME + "/tomcat/apache-tomcat-7.0.52/bin/"
TOMCAT_DIR = "/tomcat/apache-tomcat-7.0.52/bin/"
S3_URL = "https://s3-us-west-1.amazonaws.com/kibo-files/"

commands = ["options", "buildsite", "deploysite", "getsite", "setupdb", "setuptomcat", "refreshmongo", "snapshot",
			"tomcatstop", "tomcatstart", "tomcatrestart", "tail", "getdependencies"]


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def refresh_mongo(site, branch=None, version=None):
	print
	print "Refreshing local mongo db...\n"

	if branch is None:
		script_dir = MARKETLIVE_HOME + "/sites/" + site + "/trunk/source/ant/refreshLocalMongo_aws.sh"
	else:
		script_dir = MARKETLIVE_HOME + "/sites/" + site + "/branches/" + branch + "/source/ant/refreshLocalMongo_aws.sh"
	
	# Create refresh mongo script if it does not exist
	subprocess.call(["sudo touch " + script_dir], shell=True)
	subprocess.call(["sudo chmod 777 " + script_dir], shell=True)

	opener = urllib.URLopener()

	# Write refreshLocalMongo script to correct directory	
	if branch is None:
		infile = opener.open(S3_URL + "refreshLocalMongo_aws.sh")
		data = infile.read().replace("{siteName}", site)
		infile.close()

		with open(script_dir, "w") as outfile:
			outfile.write(data)

	else:
		app_dir = MARKETLIVE_HOME + "/sites/" + site + "/branches/" + branch + "/source/Apps"
		dirs = os.listdir(app_dir)
		app = dirs[0]
		print "App: " + app
		infile = opener.open(S3_URL + "refreshLocalMongo_aws-branch.sh")
		data = infile.read().replace("{siteName}", site).replace("{branchName}", branch).replace("{version}", version).replace("{app}", app)
		infile.close()

		with open(script_dir, "w") as outfile:
			outfile.write(data)

	# Run script
	print "Refreshing local mongo database..."
	subprocess.call([script_dir], shell=True)
	print bcolors.OKGREEN + "Refresh mongo completed successfully" + bcolors.ENDC


def setup_db(site):
	print
	print "Running db setup...\n"

	subprocess.call(["sudo touch " + BASE_DIR + "/setup_db.sql"], shell=True)
	subprocess.call(["sudo touch " + BASE_DIR + "/parfile.par"], shell=True)
	subprocess.call(["sudo touch " + BASE_DIR + "/setup_db.sh"], shell=True)
	subprocess.call(["sudo chmod 777 " + BASE_DIR + "/parfile.par"], shell=True)
	subprocess.call(["sudo chmod 777 " + BASE_DIR + "/setup_db.sql"], shell=True)
	subprocess.call(["sudo chmod 777 " + BASE_DIR + "/setup_db.sh"], shell=True)
	
	opener = urllib.URLopener()

	infile = opener.open(S3_URL + "ml_import_template.par")
	data = infile.read().replace("{merchant}", site)
	infile.close()

	with open("parfile.par", "w") as outfile:
		outfile.write(data)

	infile = opener.open(S3_URL + "setup_db.sql")
	data = infile.read().replace("{siteName}", site)
	infile.close()

	with open("setup_db.sql", "w") as outfile:
		outfile.write(data)

	infile = opener.open(S3_URL + "setup_db.sh")
	script_data = infile.read()
	infile.close()
	with open("setup_db.sh", "w") as outfile:
		outfile.write(script_data)

	subprocess.call(["sudo chmod 777 " + BASE_DIR + "/setup_db.sh"], shell=True)
	subprocess.call([BASE_DIR + "/setup_db.sh " + site], shell=True)

	# Remove temp files
	subprocess.call(["sudo rm -f " + BASE_DIR + "/parfile.par"], shell=True)
	subprocess.call(["sudo rm -f " + BASE_DIR + "/setup_db.sql"], shell=True)
	subprocess.call(["sudo rm -f " + BASE_DIR + "/setup_db.sh"], shell=True)

	print bcolors.OKGREEN + "Done" + bcolors.ENDC


def setup_snapshots(site):
	print
	print "Setting up snapshots...\n"

	# Create the /tmp/mongo/ directory under the site directory
	site_dir = MARKETLIVE_HOME + "/sites/" + site
	subprocess.call(["sudo mkdir -p " + site_dir + "/tmp/mongo"], shell=True)

	# Download latest snapshots of master and review
	# place those files in marketlive/sites/{site}/tmp/mongo and unzip them
	# snapshot download url: https://{merchant}-v{version}-rev.aws.marketlive.com/admin
	print "Download latest review and master snapshots and place them in " + site_dir + "/tmp/mongo"
	raw_input("Hit enter when complete: ")

	# Unzip the files
	mongo_dir = site_dir + "/tmp/mongo"
	files = [f for f in listdir(mongo_dir) if isfile(join(mongo_dir, f))]
	print "Files: " + str(files)

	for fname in files:
		if "master" in fname:
			subprocess.call(["sudo unzip " + mongo_dir + "/" + fname + " -d " + mongo_dir + "/master"], shell=True)
		elif "rev" in fname:
			subprocess.call(["sudo unzip " + mongo_dir + "/" + fname + " -d " + mongo_dir + "/review"], shell=True)

	print bcolors.OKGREEN + "Done" + bcolors.ENDC


def install_site(site, branch=None):
	print
	print "Checking out " + site + "...\n"

	# Build site url
	if branch is None:
		site_url = SVN_BASE + SITES + site + "/trunk/source"
		print site_url
		subprocess.call(["svn checkout " + site_url + " $MARKETLIVE_HOME/sites/" + site + "/trunk/source"], shell=True)
		print bcolors.OKGREEN + "Done" + bcolors.ENDC
		return

	site_url = SVN_BASE + SITES + site + "/branches/" + branch + "/source"
	print site_url

	# Get site from svn
	subprocess.call(["svn checkout " + site_url + " $MARKETLIVE_HOME/sites/" + site + "/branches/" + branch + "/source"], shell=True)
	print bcolors.OKGREEN + "Done" + bcolors.ENDC


def install_dependencies(site, branch=None):
	print
	print "Installing dependencies for " + site + "...\n"

	# Open sites.xml to parse for dependencies
	if branch is None:
		f = open(MARKETLIVE_HOME + "/sites/" + site + "/trunk/source/ant/sites.xml", "r")
	else:
		f = open(MARKETLIVE_HOME + "/sites/" + site + "/branches/" + branch + "/source/ant/sites.xml", "r")
	
	lines = f.readlines()
	f.close()

	# Parse sites.xml for required packages
	for line in lines:
		try:
			# If line does not contain this string, then it is not a dependency, continue to next line
			if not "<section " in line:
				continue
			
			# Split line into array containing path to the dependency folder
			paths = re.findall(r'\"(.+?)\"', line)

			_type = paths[0]

			# If type of dependency is source, we have already downloaded it, continue to next line
			if _type == "source":
				continue

			# Extract path from array elements
			package = paths[1]
			name = paths[2]
			version = paths[3]

			# Build the full url to the dependency folder
			tail = ""
			if "DataDeploy" in name:
				tail = _type + "/" + package.lower() + "/" + name + "-" + version
			else:
				tail = _type + "/" + package + "/" + name + "-" + version
			dependency_url = SVN_BASE + tail

			print
			print "Dependency details:"
			print "type: " + _type
			print "package: " + package
			print "name: " + name
			print "version: " + version
			print "svn url: " + dependency_url
			print "exporting " + tail + "..."

			# Download folder from svn using the svn url
			subprocess.call(["svn export " + dependency_url  + " $MARKETLIVE_HOME/" + tail], shell=True)

		except ValueError:
			pass

	print bcolors.OKGREEN + "Installed dependencies" + bcolors.ENDC


def setup_tomcat(site, branch=None, version=None):
	subprocess.call(["sudo rm -rf " + MARKETLIVE_HOME + "/tomcat/tomcat-" + site], shell=True)
	subprocess.call(["sudo rm -rf " + MARKETLIVE_HOME + "/tomcat/tomcat-" + site + "-solr"], shell=True)
	site_config = "tomcat-" + site
	solr_config = "tomcat-" + site + "-solr"
	site_config_file = site_config + ".conf"
	solr_config_file = solr_config + ".conf"
	subprocess.call(["sudo touch " + TOMCAT_SCRIPTS + "/" + site_config_file], shell=True)
	subprocess.call(["sudo touch " + TOMCAT_SCRIPTS + "/" + solr_config_file], shell=True)
	subprocess.call(["sudo chmod 777 " + TOMCAT_SCRIPTS + "/" + site_config_file], shell=True)
	subprocess.call(["sudo chmod 777 " + TOMCAT_SCRIPTS + "/" + solr_config_file], shell=True)
	
	print
	print "Setting up tomcat configuration files for site " + site + "...\n"

	opener = urllib.URLopener()

	if branch is None:
		solr_config = "solr.conf"
		site_config = "site.conf"
		infile = opener.open(S3_URL + site_config)
		site_data = infile.read().replace("{siteName}", site)
		infile.close()
		infile = opener.open(S3_URL + solr_config)
		solr_data = infile.read().replace("{siteName}", site)
		infile.close()
	else:
		solr_config = "solr-branch.conf"
		site_config = "site-branch.conf"
		infile = opener.open(S3_URL + site_config)
		site_data = infile.read().replace("{siteName}", site).replace("{branchName}", branch).replace("{version}", version)
		infile.close()
		infile = opener.open(S3_URL + solr_config)
		solr_data = infile.read().replace("{siteName}", site).replace("{branchName}", branch)
		infile.close()

	with open(TOMCAT_SCRIPTS + "/" + solr_config_file, "w") as outfile:
		outfile.write(solr_data)
	with open(TOMCAT_SCRIPTS + "/" + site_config_file, "w") as outfile:
		outfile.write(site_data)

	print bcolors.OKGREEN + "Tomcat setup" + bcolors.ENDC


def restart_tomcat(site, version=None):
	print
	print "Restarting tomcat...\n"

	# Stop tomcat processes and start up tomcat for solr and site
	subprocess.call([MARKETLIVE_HOME + TOMCAT_DIR + "shutdown.sh " + site +  " -force"], shell=True)
	subprocess.call([MARKETLIVE_HOME + TOMCAT_DIR + "shutdown.sh " + site + "-solr" + " -force"], shell=True)
	subprocess.call([MARKETLIVE_HOME + TOMCAT_DIR + "startup.sh " + site], shell=True)
	subprocess.call([MARKETLIVE_HOME + TOMCAT_DIR + "startup.sh " + site + "-solr"], shell=True)
	print bcolors.OKGREEN + "Tomcat restarted" + bcolors.ENDC
	print "python manage.py tail " + site


def start_tomcat(site):
	print
	print "Starting tomcat...\n"

	command = MARKETLIVE_HOME + TOMCAT_DIR + "startup.sh " + site
	subprocess.call([command], shell=True)
	subprocess.call([command + "-solr"], shell=True)
	print bcolors.OKGREEN + "Tomcat started" + bcolors.ENDC
	print "python manage.py tail " + site


def stop_tomcat(site, version=None):
	print
	print "Stopping tomcat...\n"
	subprocess.call([MARKETLIVE_HOME + TOMCAT_DIR + "shutdown.sh " + site + " -force"], shell=True)
	subprocess.call([MARKETLIVE_HOME + TOMCAT_DIR + "shutdown.sh " + site + "-solr" + " -force"], shell=True)
	print bcolors.OKGREEN + "Tomcat stopped" + bcolors.ENDC


def deploy_site(site, branch=None):
	print
	print "Deploying " + site + "...\n"

	# Run the ant deploy command from the correct directory
	if branch is None:
		command = "cd " + MARKETLIVE_HOME + "/sites/" + site + "/trunk/source/ant;"
	else:
		command = "cd " + MARKETLIVE_HOME + "/sites/" + site + "/branches/" + branch + "/source/ant;"
		
	command += "ant deployClean -Ddeploy.name=" + site
	subprocess.call([command], shell=True)
	print bcolors.OKGREEN + site + " deployed" + bcolors.ENDC


def get_site_version(site, branch=None):
	# Open sites.xml to parse for dependencies

	if branch is None:
		f = open(MARKETLIVE_HOME + "/sites/" + site + "/trunk/source/ant/sites.xml", "r")
	else:
		f = open(MARKETLIVE_HOME + "/sites/" + site + "/branches/" + branch + "/source/ant/sites.xml", "r")

	lines = f.readlines()
	f.close()

	for line in lines:
		try:
			# If line does not contain this string, then it is not a dependency, continue to next line
			if not "<section " in line:
				continue
			if not "Marketlive-" in line:
				continue

			paths = re.findall(r'\"(.+?)\"', line)
			version = paths[3].replace(".", "")[:3]
			return version

		except ValueError:
			pass
	return None


def display_options():
	print
	print bcolors.UNDERLINE + bcolors.OKGREEN + "Commands:" + bcolors.ENDC

	for command in commands:
		print "- " + command + " -options"

	print
	print bcolors.UNDERLINE + "Example usage:" + bcolors.ENDC + " python manage.py runserver steinmart"
	print


if __name__=="__main__":
	num_args = len(sys.argv)

	# At least one argument is required
	if num_args < 2:
		print
		print "usage: python manage.py <command> <options>"
		print bcolors.BOLD + bcolors.FAIL + "error: Must provide a valid argument" + bcolors.ENDC
		print
		sys.exit(1)

	# Invalid command
	if num_args >= 2 and sys.argv[1] not in commands:
		print
		print "usage: python manage.py <command> <options>"
		display_options()
		print bcolors.BOLD + bcolors.FAIL + "error: Unrecognized command '" +sys.argv[1] + "'" + bcolors.ENDC
		print
		sys.exit(1)


	command = sys.argv[1]

	if command == "options":
		display_options()

	elif command == "getdependencies":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <site>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide a site name" + bcolors.ENDC
			print
			sys.exit(1)

		site = sys.argv[2]
		install_dependencies(site)

	elif command == "tail":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <site>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide a site name" + bcolors.ENDC
			print
			sys.exit(1)

		if num_args == 3:
			site = sys.argv[2]
			command = "tail -1000f " + MARKETLIVE_HOME + "/tomcat/tomcat-" + site + "/logs/catalina.out"
			subprocess.call([command], shell=True)
		else:
			site = sys.argv[2]
			version = sys.argv[3]
			command = "tail -1000f " + MARKETLIVE_HOME + "/tomcat/tomcat-" + site + version + "/logs/catalina.out"
			subprocess.call([command], shell=True)


	elif command == "refreshmongo":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <site>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide a site name" + bcolors.ENDC
			print
			sys.exit(1)

		if num_args == 3:
			site  = sys.argv[2]
			refresh_mongo(site)
		else:
			site = sys.argv[2]
			branch = sys.argv[3]
			version = sys.argv[4]
			refresh_mongo(site, branch, version)

	elif command == "deploysite":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <merchant> <branch>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide merchant name and branch name" + bcolors.ENDC
			print
			sys.exit(1)

		if num_args == 3:
			site = sys.argv[2]
			deploy_site(site)
		else:
			site = sys.argv[2]
			branch = sys.argv[3]
			deploy_site(site, branch)

	elif command == "tomcatstart":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <merchant> <version>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide merchant name and version number" + bcolors.ENDC
			print
			sys.exit(1)

		if num_args == 3:
			site = sys.argv[2]
			start_tomcat(site)
		else:
			site = sys.argv[2]
			version = sys.argv[3]
			start_tomcat(site)

	elif command == "tomcatstop":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <merchant> <version>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide merchant name and version number" + bcolors.ENDC
			print
			sys.exit(1)

		if num_args == 3:
			site = sys.argv[2]
			stop_tomcat(site)
		else:
			site = sys.argv[2]
			version = sys.argv[3]
			stop_tomcat(site)

	elif command == "tomcatrestart":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <merchant> <version>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide merchant name and version number" + bcolors.ENDC
			print
			sys.exit(1)

		if num_args == 3:
			site = sys.argv[2]
			restart_tomcat(site)
		else:
			site = sys.argv[2]
			version = sys.argv[3]
			restart_tomcat(site)

	elif command == "snapshot":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <site>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide merchant name" + bcolors.ENDC
			print
			sys.exit(1)

		site = sys.argv[2]
		setup_snapshots(site)

	elif command == "setuptomcat":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <site>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide a site name" + bcolors.ENDC
			print
			sys.exit(1)

		if num_args == 3:
			site = sys.argv[2]
			setup_tomcat(site)
		elif num_args == 5:
			site = sys.argv[2]
			branch = sys.argv[3]
			version = sys.argv[4]
			setup_tomcat(site, branch, version)

	elif command == "setupdb":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <site>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide a site name" + bcolors.ENDC
			print
			sys.exit(1)

		site = sys.argv[2]
		setup_db(site)

	elif command == "getsite":
		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <site>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide a site name" + bcolors.ENDC
			print
			sys.exit(1)

		if num_args == 3:
			site = sys.argv[2]
			install_site(site)
		else:
			site = sys.argv[2]
			branch = sys.argv[3]
			install_site(site, branch)

	elif command == "buildsite":

		if num_args < 3:
			print
			print "usage: python manage.py " + command + " <merchant> <optional branch>"
			print bcolors.BOLD + bcolors.FAIL + "error: Must provide merchant name" + bcolors.ENDC
			print
			sys.exit(1)

		site = sys.argv[2]

		# Build a specific branch of the website
		if num_args == 4:
			branch = sys.argv[3]
			print "Building " + site + " branch: " + branch + "..."
			install_site(site, branch)
			version = get_site_version(site, branch)
			install_dependencies(site, branch)
			setup_db(site)
			setup_tomcat(site, branch, version)
			setup_snapshots(site)
			refresh_mongo(site, branch, version)
			deploy_site(site, branch)
		
		# Build trunk
		elif num_args == 3:
			branch = "trunk"
			print "Building " + site + " trunk..."
			site = sys.argv[2]
			install_site(site)
			version = get_site_version(site)
			install_dependencies(site)
			setup_db(site)
			setup_tomcat(site)
			setup_snapshots(site)
			refresh_mongo(site)
			deploy_site(site)

		print bcolors.BOLD + bcolors.OKGREEN + "Build complete" + bcolors.ENDC
		print bcolors.BOLD + bcolors.OKGREEN + "Build:" + bcolors.ENDC
		print bcolors.BOLD + bcolors.OKGREEN + "Merchant: " + site + bcolors.ENDC
		print bcolors.BOLD + bcolors.OKGREEN + "Branch: " + branch + bcolors.ENDC
		print bcolors.BOLD + bcolors.OKGREEN + "Version: " + version + bcolors.ENDC
		print "python manage.py tomcatstart " + site
