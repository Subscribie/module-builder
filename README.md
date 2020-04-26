# Builder module

The builder module is responsible for building new subscribie sites.

- When a new site is created (via /start-building) , all the
  data to build that site (in yaml) is sent to the builder module which builds 
  a new subscribie site
- Each site is defined in a yaml file, and a clone of the Subscribie repo
- Each site runs as a uwsgi 'vassal' which allows new sites to come online
  without having to restart the web server
