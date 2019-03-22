import os
from io import BytesIO

from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from requests_toolbelt.multipart import decoder
from ssc.audio_analysis.acr_api_requests import identify_audio, upload_audio

from ssc.Workspaces.workspaces import *

from ssc.Invites.invites import fetch_user_invites, process_invite, insert_user_invite

from ssc.Workspaces.workspaces import delete_workspace, update_admin, \
    create_workspace_with_users, create_workspace_only, fetch_workspace_files, \
    delete_user_from_workspace

from ssc.Users.users import fetch_users, add_user, fetch_user_workspaces
from ssc.audiokey_api.audiokey import add_audio_key

app = Flask(__name__, template_folder = 'testflask/templates')
CORS(app)


@app.route("/")
def homeDummy():
    return 'Home';


@app.route("/api/users")
def get_users():
    return fetch_users()


@app.route("/api/users", methods = ['POST'])
def post_user():
    username = request.json['username']
    password = request.json['password']
    return add_user(username, password)


@app.route('/api/users/<username>', methods = ["GET"])
def get_user_workspaces(username):
    list_of_workspaces = fetch_user_workspaces(username)
    return jsonify({'workspaces': list_of_workspaces})


@app.route("/deleteUser", methods = ['DELETE'])
def delete_user():
    return delete_user_from_workspace(request.json)


@app.route("/api/invites/<username>", methods = ["POST"])
def update_invite(username):
    if (not request.json) | ('accept' not in request.json) | ('workspace' not in request.json):
        abort(400)

    res = process_invite(username, request.json)
    return jsonify({'invitesProcessed': res});


@app.route("/api/invites/<username>", methods = ["GET"])
def get_user_invites(username):
    list_of_invites = fetch_user_invites(username)
    res = {'invites': list_of_invites}
    return jsonify(res);


@app.route("/api/invites", methods = ["POST"])
def invite_user():
    if (not request.json) | ('username' not in request.json) \
            | ('workspace' not in request.json) | ('invitedBy' not in request.json):
        abort(400)

    res = insert_user_invite(request.json)
    res_json = {'user_invited': res}
    if (res == False): res_json['error'] = 'Could not invite user. ' \
                                           'Check user is admin or invite still exists'
    return jsonify(res_json);


@app.route('/api/workspaces', methods = ['POST'])
def handle_create_workspace():
    if (not request.json) | ('name' not in request.json) | ('admin' not in request.json):
        abort(400)
    else:
        if ('users' in request.json):
            res = create_workspace_with_users(request.json)
            if (res == len(request.json['users'])):
                res_json = {'workspace_added': True}
            elif (res != 0):
                res_json = {'workspace_added': False,
                            'error': 'Workspace added but not all users added.'}
            else:
                res_json = {'workspace_added': False,
                            'error': 'Workspace could not be added.'}
        else:
            res = create_workspace_only(request.json)
            if (res):
                res_json = {'workspace_added': True}
            else:
                res_json = {'workspace_added': False,
                            'error': 'Could not add workspace or set admin.'}

        return jsonify(res_json);


@app.route("/api/workspaces", methods = ["DELETE"])
def handle_delete_workspace():
    if (not request.json) | ('workspace' not in request.json) | ('deleted_by' not in request.json):
        abort(400)

    res = delete_workspace(request.json)
    res_json = {'workspace_deleted': res}
    if (res == False): res_json['error'] = 'Could not delete workspace. ' \
                                           'Check user is admin or workspace still exists'
    return jsonify(res_json);


@app.route("/api/workspaces/<name>", methods = ["GET"])
def get_workspace_file(name):
    list_of_files = fetch_workspace_files(name)
    res = {'files': list_of_files}
    return jsonify(res);


@app.route("/api/workspaces/<workspace_name>", methods = ["PUT"])
def handle_update_workspace(workspace_name):
    if (not request.json) | ('username' not in request.json) \
            | ('admin_username' not in request.json) | ('make_admin' not in request.json):
        abort(400)

    res = update_admin(workspace_name, request.json)
    print(res)
    res_json = {'workspace_admin_updated': res}
    if (res == False): res_json['error'] = 'Could not update workspace. ' \
                                           'Check admin user is an admin'

    return jsonify(res_json);


@app.route("/api/audiokey", methods = ["POST"])
def post_audio_key():
    file = request.files["file"].read()
    audio_file_copy1 = BytesIO(file)
    audio_file_copy2 = BytesIO(file)
    sample_bytes = len(file)
    session_id = request.values.get("session_id")
    file_name = request.values.get("filename")
    acr_response = identify_audio(audio_file_copy1, sample_bytes)
    if acr_response["status"]["msg"] == 'No result':
        acr_upload_response = upload_audio(audio_file_copy2, file_name, session_id)
        add_audio_key(acr_upload_response["acr_id"], session_id)
        return jsonify({"notRecognised": True})
    if 'custom_files' in acr_response["metadata"].keys():
        print('custom found')
        return jsonify({"fileError": True})
    if acr_response["status"]["msg"] == 'Success':
        add_audio_key(acr_response["metadata"]["music"][0]["acrid"], session_id)
        return jsonify({"title": acr_response["metadata"]["music"][0]["title"],
                        "artist": acr_response["metadata"]["music"][0]["artists"][0]["name"]})

    return jsonify('Error check')


# if (not request.json) | ('audio_key' not in request.json) | ('session_id' not in request.json):
#     abort(400)
#

#


if __name__ == "__main__":
    # app.run(debug=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host = '0.0.0.0', port = port)
