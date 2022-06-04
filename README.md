# Builder module

The builder module is responsible for building new subscribie sites.

- When a new site is created (via /start-building) , all the
  data to build that site (in yaml) is sent to the builder module which builds 
  a new subscribie site
- Each site is defined in a yaml file, and a clone of the Subscribie repo
- Each site runs as a uwsgi 'vassal' which allows new sites to come online
  without having to restart the web server
  
  
## How do I enable the builder module?

1. Create a directory for subscribie modules e.g `mkdir ~/subscribie-modules`
2. Clone this repo into that folder `git clone git@github.com:Subscribie/module-builder.git`
3. In your **Subscribie** repo `.env` file set `MODULES_PATH` equal to your subscribie modules directry. e.g. "`MODULES_PATH="/home/sam/subscribie-modules/"`
4. In your subscribie database (e.g. data.db) insert "`builder`" into the modules table `INSERT INTO module (name) VALUES ('builder');` this will cause Subscribie to attemp importing the `module-builder` into Subscribie. Module builder is a [flask blueprint]([url](https://flask.palletsprojects.com/en/2.1.x/blueprints/)).
5. Make sure your 
6. Restart subscribie **Subscribie** repo `.env` file `THEME_NAME` is set to `THEME_NAME=builder`
