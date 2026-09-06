from flask import Flask, render_template, request, redirect, send_from_directory, jsonify
import os, json

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
IMAGE_DIR = os.path.join(STATIC_DIR, "images")
SCENE_FILE = os.path.join(STATIC_DIR, "scenes.json")

os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------------- INIT ----------------
if not os.path.exists(SCENE_FILE):
    with open(SCENE_FILE, "w") as f:
        json.dump({}, f)

def get_opposite(direction):
    return {
        "forward": "back",
        "back": "forward",
        "left": "right",
        "right": "left"
    }.get(direction, "")

def load_scenes():
    with open(SCENE_FILE, "r") as f:
        return json.load(f)

def save_scenes(data):
    with open(SCENE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- AUTO LINKING LOGIC ----------------

def auto_link_scenes(scenes):

    ids = list(scenes.keys())

    for i, sid in enumerate(ids):

        scene = scenes[sid]

        # Skip manual scenes
        if scene.get("manual", False):
            continue

        # forward link
        if scene.get("forward","") == "" and i + 1 < len(ids):
            scene["forward"] = ids[i + 1]

        # backward link
        if scene.get("back","") == "" and i - 1 >= 0:
            scene["back"] = ids[i - 1]

        # ensure fields exist
        scene.setdefault("left","")
        scene.setdefault("right","")

    return scenes
# ---------------- ROUTES ----------------

@app.route("/")
def admin():
    scenes = load_scenes()
    return render_template("admin.html", scenes=scenes)

@app.route("/viewer")
def viewer():
    return render_template("viewer.html")

@app.route("/builder")
def builder():
    scenes = load_scenes()
    return render_template("builder.html", scenes=scenes)

@app.route("/upload", methods=["POST"])
def upload():
    scenes = load_scenes()

    file = request.files.get("image")
    if not file:
        return redirect("/")

    scene_id = f"scene{len(scenes) + 1}"
    filename = f"{scene_id}.jpg"
    file.save(os.path.join(IMAGE_DIR, filename))

    scenes[scene_id] = {
        "image": filename,
        "forward": "",
        "back": "",
        "left": "",
        "right": "",
        "manual": False
    }

    scenes = auto_link_scenes(scenes)
    save_scenes(scenes)
    return redirect("/")

# --------- MANUAL OVERRIDE --------- 

@app.route("/edit-directions", methods=["POST"])
def edit_directions():

    scenes = load_scenes()

    sid = request.form.get("scene_id")

    if sid not in scenes:
        return redirect("/")

    directions = ["forward", "back", "left", "right"]
    override = request.form.get("override")

    # remove old reverse links
    if not override:

        for d in directions:

            target = scenes[sid].get(d)

            if target and target in scenes:

                opposite = get_opposite(d)

                if scenes[target].get(opposite) == sid:
                    scenes[target][opposite] = ""

    # update directions
    for d in directions:

        new_target = request.form.get(d)

        if new_target and new_target in scenes:

            scenes[sid][d] = new_target

            if not override:

                opposite = get_opposite(d)

                scenes[new_target][opposite] = sid

        else:
            scenes[sid][d] = ""

    scenes[sid]["manual"] = True

    save_scenes(scenes)

    return redirect("/")

@app.route("/builder-upload", methods=["POST"])
def builder_upload():

    scenes = load_scenes()

    current_scene = request.form.get("scene")
    direction = request.form.get("direction")
    file = request.files.get("image")

    if not file or current_scene not in scenes:
        return redirect("/builder")

    new_scene_id = f"scene{len(scenes)+1}"
    filename = f"{new_scene_id}.jpg"

    file.save(os.path.join(IMAGE_DIR, filename))

    scenes[new_scene_id] = {
        "image": filename,
        "forward": "",
        "back": "",
        "left": "",
        "right": "",
        "manual": True
    }

    if direction and current_scene in scenes:

        scenes[current_scene][direction] = new_scene_id

        opposite = get_opposite(direction)

        if opposite:
            scenes[new_scene_id][opposite] = current_scene

    save_scenes(scenes)

    return redirect(f"/builder?scene={new_scene_id}")

@app.route("/connect-scenes", methods=["POST"])
def connect_scenes():

    scenes = load_scenes()
    data = request.get_json()

    from_scene = data["from_scene"]
    to_scene = data["to_scene"]
    direction = data["direction"]

    reverse = {
        "forward": "back",
        "back": "forward",
        "left": "right",
        "right": "left"
    }

    if from_scene in scenes and to_scene in scenes:

        scenes[from_scene][direction] = to_scene
        scenes[to_scene][reverse[direction]] = from_scene

        save_scenes(scenes)

    return jsonify({"status":"ok"})

# --------- REORDER WITH AUTO RELINK ---------

@app.route("/reorder-scenes", methods=["POST"])
def reorder_scenes():
    data = request.get_json()
    order = data.get("order", [])

    scenes = load_scenes()
    new_scenes = {}

    for sid in order:
        if sid in scenes:
            new_scenes[sid] = scenes[sid]

    new_scenes = auto_link_scenes(new_scenes)
    save_scenes(new_scenes)

    return jsonify({"status": "ok"})


# --------- MENU ---------

@app.route("/menu.json")
def menu_json():
    with open("static/menu.json") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/menu")
def menu_manager():

    with open("static/menu.json") as f:
        menu = json.load(f)

    with open("static/scenes.json") as f:
        scenes = json.load(f)

    return render_template(
        "menu_manager.html",
        menu=menu,
        scenes=scenes
    )


@app.route("/add-block", methods=["POST"])
def add_block():

    block = request.form["block_name"]

    with open("static/menu.json") as f:
        menu = json.load(f)

    if block not in menu:
        menu[block] = {}

    with open("static/menu.json", "w") as f:
        json.dump(menu, f, indent=4)

    return redirect("/menu")


@app.route("/add-floor", methods=["POST"])
def add_floor():

    block = request.form["block"]
    floor = request.form["floor_name"]
    scene = request.form["scene_id"]

    with open("static/menu.json") as f:
        menu = json.load(f)

    menu[block][floor] = scene

    with open("static/menu.json", "w") as f:
        json.dump(menu, f, indent=4)

    return redirect("/menu")


@app.route("/rename-block", methods=["POST"])
def rename_block():

    old = request.form["old_name"]
    new = request.form["new_name"]

    with open("static/menu.json") as f:
        menu = json.load(f)

    if old in menu:
        menu[new] = menu.pop(old)

    with open("static/menu.json", "w") as f:
        json.dump(menu, f, indent=4)

    return redirect("/menu")


@app.route("/delete-block", methods=["POST"])
def delete_block():

    block = request.form["block_name"]

    with open("static/menu.json") as f:
        menu = json.load(f)

    if block in menu:
        del menu[block]

    with open("static/menu.json", "w") as f:
        json.dump(menu, f, indent=4)

    return redirect("/menu")


@app.route("/update-floor", methods=["POST"])
def update_floor():

    data = request.get_json()

    block = data.get("block")
    old_floor = data.get("old_floor")
    new_floor = data.get("new_floor")
    new_scene = data.get("scene_id")

    with open("static/menu.json") as f:
        menu = json.load(f)

    if block not in menu or old_floor not in menu[block]:
        return jsonify({"status":"error"})

    # get current scene
    current_scene = menu[block][old_floor]

    # decide final values
    final_floor = new_floor if new_floor else old_floor
    final_scene = new_scene if new_scene else current_scene

    # remove old
    del menu[block][old_floor]

    # update new
    menu[block][final_floor] = final_scene

    with open("static/menu.json","w") as f:
        json.dump(menu,f,indent=4)

    return jsonify({"status":"ok"})


@app.route("/delete-floor", methods=["POST"])
def delete_floor():

    block = request.form["block"]
    floor = request.form["floor"]

    with open("static/menu.json") as f:
        menu = json.load(f)

    if block in menu and floor in menu[block]:
        del menu[block][floor]

    with open("static/menu.json", "w") as f:
        json.dump(menu, f, indent=4)

    return redirect("/menu")



# --------- HOTSPOT ---------

@app.route("/add-hotspot", methods=["POST"])
def add_hotspot():

    data = request.get_json()

    scene = data["scene"]
    pitch = data["pitch"]
    yaw = data["yaw"]
    text = data["text"]

    with open("static/scenes.json") as f:
        scenes = json.load(f)

    if "hotspots" not in scenes[scene]:
        scenes[scene]["hotspots"] = []

    scenes[scene]["hotspots"].append({
        "pitch": pitch,
        "yaw": yaw,
        "text": text
    })

    with open("static/scenes.json","w") as f:
        json.dump(scenes,f,indent=4)

    return {"status":"ok"}



@app.route("/update-hotspot", methods=["POST"])
def update_hotspot():

    data=request.json

    with open("static/scenes.json") as f:
        scenes=json.load(f)

    for h in scenes[data["scene"]]["hotspots"]:
        if h["text"]==data["oldText"]:
            h["text"]=data["newText"]

    with open("static/scenes.json","w") as f:
        json.dump(scenes,f,indent=4)

    return {"status":"ok"}





@app.route("/delete-hotspot", methods=["POST"])
def delete_hotspot():

    data=request.json

    with open("static/scenes.json") as f:
        scenes=json.load(f)

    scenes[data["scene"]]["hotspots"]=[
        h for h in scenes[data["scene"]]["hotspots"]
        if h["text"]!=data["text"]
    ]

    with open("static/scenes.json","w") as f:
        json.dump(scenes,f,indent=4)

    return {"status":"ok"}


# --------- DELETE ---------

@app.route("/delete-scene", methods=["POST"])
def delete_scene():
    scenes = load_scenes()
    data = request.get_json()
    sid = data.get("scene_id")

    if sid in scenes:
        del scenes[sid]

        for s in scenes.values():
            for d in ["forward", "back", "left", "right"]:
                if s[d] == sid:
                    s[d] = ""

        scenes = auto_link_scenes(scenes)
        save_scenes(scenes)

    return jsonify({"status": "deleted"})

# ---------------- STATIC ----------------

@app.route("/scenes.json")
def scenes_json():
    response = send_from_directory(STATIC_DIR, "scenes.json")
    response.headers["Cache-Control"] = "no-store"
    return response

@app.route("/static/images/<path:filename>")
def images(filename):
    return send_from_directory(IMAGE_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True)
