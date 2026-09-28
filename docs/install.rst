Install
=========

Prerequisites
-------------

Install the command line tools used by the development workflow:

* ``uv``
* ``just``
* PostgreSQL server/client binaries such as ``postgres``, ``initdb``,
  ``createdb``, ``dropdb``, ``createuser``, and ``psql``
* Real S3 media credentials in ``.env``:
  ``DJANGO_AWS_ACCESS_KEY_ID``, ``DJANGO_AWS_SECRET_ACCESS_KEY``,
  ``DJANGO_AWS_STORAGE_BUCKET_NAME``, and ``CLOUDFRONT_DOMAIN``

The configured S3 bucket or CloudFront distribution must return an
``Access-Control-Allow-Origin`` response that permits the public site origin for
anonymous ``GET`` requests. The portfolio Hero requests its editorial reveal image with
``crossorigin="anonymous"`` before drawing it into a WebGL texture. If CORS is absent or
the media response cannot be decoded, the page deliberately retains the generated reveal
instead of disabling the Hero.

For CloudFront, configure the media cache behaviour in one of these two ways:

* forward the browser's ``Origin`` header to S3 (for example with the managed
  ``CORS-S3Origin`` origin request policy) **and** include ``Origin`` in the associated
  cache-policy key, so a response cached for a crawler without ``Origin`` cannot be
  reused for the canvas request; or
* attach a response-headers policy that always adds the intended
  ``Access-Control-Allow-Origin`` value for these public media responses.

After deployment, copy the Hero image's resolved ``currentSrc`` URL from the browser and
verify the real public-site origin rather than only testing the S3 origin directly:

.. code-block:: console

   curl --head --header 'Origin: https://www.example.com' 'https://media.example.com/path/to/rendition.jpg'

The response must contain ``Access-Control-Allow-Origin`` with that site origin (or
``*`` for intentionally public credential-free media). Repeat after a request without
``Origin`` to catch an unsafe CloudFront cache configuration.

Local database
--------------

The project uses a repository-local PostgreSQL data directory at
``databases/postgres``. It is created automatically the first time you start
PostgreSQL through ``just``:

.. code-block:: console

   $ just postgres

The same bootstrap is used by the Procfile, so normal development startup also
works on a fresh machine:

.. code-block:: console

   $ just dev

Restore production data locally
-------------------------------

The production restore command fetches a fresh PostgreSQL dump over SSH from
``root@wersdoerfer.de`` and restores it into the local ``homepage`` database. It
expects only PostgreSQL to be running locally. Start PostgreSQL directly with
``just postgres`` in one terminal, then restore from another:

.. code-block:: console

   $ just postgres
   $ uv run commands.py production-db-to-local

Do not use ``uvx honcho start postgres`` for this restore flow; the restore
command intentionally exits when it sees a running ``honcho`` process.

The command no longer uses the legacy Ansible Vault files in ``deploy/``. To
override the SSH host or database names, see:

.. code-block:: console

   $ uv run commands.py production-db-to-local --help

Production
==========

To deploy this project on a production machine, follow those steps:
 * apt install python3-pip supervisor postgresql
 * pip3 install uv
 * Create PostgreSQL database and user for the application
 * Configure environment variables for database access
 * ln -s /home/homepage/homepage/supervisor.conf /etc/supervisor/conf.d/homepage.conf
 * supervisorctl reload
 * supervisorctl start homepage
