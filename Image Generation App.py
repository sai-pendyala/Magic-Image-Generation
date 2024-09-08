from fasthtml.common import *
from fastcore.parallel import threaded
import os
import requests
import uuid

tables = database("data/gens.db").t
gens = tables.gens
if gens not in tables:
    gens.create(prompt=str, id=int, model=str, session_id=str, folder=str, pk="id")
Generation = gens.dataclass()

gridlink = Link(
    rel="stylesheet",
    href="https://cdnjs.cloudflare.com/ajax/libs/flexboxgrid/6.3.1/flexboxgrid.min.css",
    type="text/css",
)

app = FastHTML(hdrs=(picolink, gridlink))


@app.get("/")
def home(session):
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    inp = Input(id="new_prompt", name="prompt", placeholder="Enter a prompt")
    model_dropdown = Select(
        Option("Flux", value="flux"),
        Option("Flux Realism", value="flux-realism"),
        Option("Flux Anime", value="flux-anime"),
        Option("Flux 3D", value="flux-3d"),
        Option("Turbo", value="turbo"),
        name="model",
    )
    add = Form(
        Group(inp, model_dropdown, Button("Generate")),
        hx_post="/",
        hx_target="#gen-list",
        hx_swap="afterbegin",
    )
    gen_containers = [
        generation_preview(g, session)
        for g in gens(limit=8, where=f"session_id=='{session['session_id']}'")
    ]
    gen_list = Div(
        *reversed(gen_containers),
        id="gen-list",
        cls="row",
    )
    return Title("Image Generation"), Main(
        Hgroup(
            H1("Magic Image Generation"),
            P(str(session)),
        ),
        add,
        gen_list,
        cls="container-fluid",
    )


@app.post("/")
def post(prompt: str, model: str, session):
    if "session_id" not in session:
        return "No session ID"
    folder = f"data/gens/{str(uuid.uuid4())}"
    os.makedirs(folder, exist_ok=True)
    g = gens.insert(
        Generation(
            prompt=prompt, folder=folder, model=model, session_id=session["session_id"]
        )
    )
    generate_and_save(g.prompt, g.id, g.folder, g.model)
    clear_inp = Input(
        id="new_prompt", name="prompt", placeholder="Enter a prompt", hx_swap_oob="true"
    )
    return generation_preview(g, session), clear_inp


@threaded
def generate_and_save(prompt, id, folder, model):
    url = f"https://pollinations.ai/p/{prompt}?width=1024&height=1024&model={model}&seed=-1&nologo=true&enhance=true"
    response = requests.get(url)
    with open(f"{folder}/{id}.jpg", "wb") as file:
        file.write(response.content)
    return True


def generation_preview(g, session):
    if "session_id" not in session:
        return "No session ID"
    if g.session_id != session["session_id"]:
        return "Wrong session ID"
    grid_cls = "box col-xs-12 col-sm-6 col-md-4 col-lg-3"
    image_path = f"{g.folder}/{g.id}.jpg"
    if os.path.exists(image_path):
        return Div(
            Card(
                Img(
                    src=image_path,
                    alt="Card image",
                    cls="card-img-top",
                ),
                Div(P(B("Prompt: "), g.prompt, cls="card-text"), cls="card-body"),
            ),
            id=f"gen-{g.id}",
            cls=grid_cls,
        )
    else:
        # busy = PicoBusy()
        return Div(
            f"Generating image for '{g.prompt}'...",
            id=f"gen-{id}",
            hx_get=f"/gens/{g.id}",
            hx_trigger="every 2s",
            hx_swap="outerHTML",
            cls=grid_cls,
        )


@app.get("/gens/{id}")
def preview(id: int, session):
    return generation_preview(gens.get(id), session)


@app.get("/{fname:path}.{ext:static}")
def static(fname: str, ext: str):
    return FileResponse(f"{fname}.{ext}")


serve()
