# pylint: disable=logging-fstring-interpolation

"""
`ato view`
"""

import logging

import click

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

from waitress import serve

from atopile import errors
from atopile.cli.common import project_options
from atopile.config import BuildContext

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


viewer_app = Flask(__name__, static_folder='../viewer/dist', static_url_path='')
# Enable CORS for all domains on all routes
CORS(viewer_app)

@viewer_app.route('/data')
def send_json():
    build_dir_path = viewer_app.config.get('build_dir_path', 'Default value if not set')
    #TODO: handle other builds than defaults
    view_data_path = os.path.join(build_dir_path, 'default.view.json')
    with open(view_data_path, 'r') as file:
        data = json.load(file)
    return jsonify(data)


@viewer_app.route('/')
def home():
    return send_from_directory(viewer_app.static_folder, 'index.html')


@click.command()
@project_options
def view(build_ctxs: list[BuildContext]):
    log.info("Spinning up the viewer")

    if len(build_ctxs) == 0:
        errors.AtoNotImplementedError("No build contexts found.")
    elif len(build_ctxs) == 1:
        build_ctx = build_ctxs[0]
    else:
        build_ctx = build_ctxs[0]
        errors.AtoNotImplementedError(
            f"Using top build config {build_ctx.name} for now. Multiple build configs not yet supported."
        ).log(log, logging.WARNING)

    viewer_app.config['build_dir_path'] = build_ctx.build_path
    serve(viewer_app, host="127.0.0.1", port=8080)
