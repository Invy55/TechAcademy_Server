import pathlib
from os import path
import argparse
import json
import urllib.request
import subprocess
import shutil

ROSSO = "\033[91m"
VERDE = "\033[92m"
GIALLO = "\033[93m"
RESET = "\033[0m\n"

# Cartelle da ignorare durante la copia degli overrides
ignored_dirs = ['shader']
# Mod da ignorare perchè client side, purtroppo non hanno i tag settati corretamente su curse forge e vengono quindi scaricate comunque
ignored_mods = [447673, # Sodium Extra
                511319, # Reese's Sodium Options
                1103431, # Sodium/Embeddium Options API
                551736, # Sodium/Embeddium Dynamic Lights
                #849519, # e4mc
                938643, # Melody
                561885, # Just Zoom
                627557, # Complementary Shaders - Reimagined
                978510, # Skygleam Shaders
                322506, # BSL Shaders
                385587, # Complementary Shaders - Unbound
                678384, # Solas Shader
                1085570, # BSL Shaders - Classic
                431203, # MakeUp - Ultra Fast | Shaders
                855381, # FastPBR Shader
                569743, # Stracciatella Shaders
                ]

# Crea il parser
parser = argparse.ArgumentParser()
parser.add_argument('folder', help="Cartella del modapack da cui creare il server")
parser.add_argument('-o', '--output', help="Cartella in cui creare il server", default='server')

# Leggi gli args passati
args = parser.parse_args()

# Trucco per cambiare l'user agent di urllib senza usare requests che richiederebbe l'installazione di un pacchetto esterno
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0')]
urllib.request.install_opener(opener)

# Crea la cartella di output del server dal nome passato
server_dir = pathlib.Path(args.output)
server_dir.mkdir(exist_ok=True)

# Leggi il manifest.json e prendi le informazioni necessarie
try:
    manifest = json.load(open(path.join(args.folder, 'manifest.json')))
except FileNotFoundError:
    print(f"{ROSSO}File {path.join(args.folder, 'manifest.json')} non trovato. Assicurati di aver passato la cartella del modapack corretta.", end=RESET)
    exit(1)

overrides = path.join(args.folder, 'overrides')
if not path.exists(overrides):
    print(f"{GIALLO}Warning: Cartella {overrides} non trovata. Assicurati di aver passato la cartella del modapack corretta.", end=RESET)
    overrides = None

mods = manifest.get('files', None)

# Prendi il primo mod loader, TODO aggiungere il supporto per più mod loader
neoforge_version = manifest.get('minecraft', {}).get('modLoaders', {})[0].get('id', None)
if not neoforge_version:
    print("{ROSSO}Versione di neoforge non trovata nel manifest. Assicurati di aver passato la cartella del modapack corretta.", end=RESET)
    exit(1)

# Prendi la versione di neoforge dal manifest e scarica il jar
neoforge_version = neoforge_version.strip()
neoforge_link = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{neoforge_version.split('-', 1)[1]}/{neoforge_version}-installer.jar"
neoforge_path = path.join(server_dir, f"{neoforge_version}.jar")
urllib.request.urlretrieve(neoforge_link, neoforge_path)

# Controlla se il file è stato scaricato correttamente e aggiungi le istruzioni per l'installazione
if not path.exists(neoforge_path):
    print(f"Errore durante il download di {neoforge_link}", end=RESET)
    exit(1)

with open(path.join(server_dir, 'ISTRUZIONI.txt'), 'w', encoding= "utf-8") as istruzioni:
    istruzioni.write(f"""Istruzioni per l'installazione del server Neoforge (attenzione il simbolo del dollaro è inserito solo per evidenziare che si tratta di un comando, NON copiarlo nel terminale):

1. Assicurati di avere Java installato e configurato

2. Apri il terminale e naviga nella cartella del server

3. Installa il server {neoforge_version} con il comando:
$ java -jar {neoforge_version}.jar --installServer

4. Una volta completata l'installazione puoi eliminare il file {neoforge_version}.jar

5. Avvia il server con:
- Windows:
doppio click su run.bat
- Linux:
$ ./run.sh
Attenzione: se non funziona devi dare il permesso di esecuzione al file run.sh con il seguente comando (SOLO LA PRIMA VOLTA):
$ chmod +x run.sh

6. Potrebbe venirti chiesto di accettare l'eula direttamente nel terminale, in quel caso scrivi true e premi invio. Altrimenti, una volta che si è chiuso il server, apri il file eula.txt e accetta l'eula mettendo eula=true al posto di eula=false""")

# # Esegui il comando per installare il server
# subprocess.run(["java", "-jar", neoforge_path, "--installServer", server_dir], shell=True)
# #subprocess.run(["powershell.exe", "$Env:Path.Split(';')"], shell=True)
# pathlib.Path(neoforge_path).unlink()

# Parte delle mod
mods_dir = path.join(server_dir, 'mods')
pathlib.Path(mods_dir).mkdir(exist_ok=True)

errored_mods = []
client_only_mods = []
server_mods = []
for mod in mods:
    project_id = mod.get('projectID', None)
    file_id = mod.get('fileID', None)
    if project_id in ignored_mods:
        continue

    if not project_id or not file_id:
        print(f"{ROSSO}Errore: Mod {mod} non ha un ID valido.", end=RESET)
        errored_mods.append(mod)
        continue
    
    print(f"Fetching di {project_id}...", end=RESET)
    #https://www.curseforge.com/api/v1/mods/962544/files?pageIndex=0&pageSize=20&sort=dateCreated&sortDescending=true&gameVersionId=11779&gameFlavorId=6&removeAlphas=true
    #gameVersionId=11779&
    r = urllib.request.urlopen(f"https://www.curseforge.com/api/v1/mods/{project_id}/files?pageIndex=0&pageSize=50&sort=dateCreated&sortDescending=true&gameFlavorId=6&removeAlphas=false")

    try:
        response = json.loads(r.read())
    except json.JSONDecodeError:
        print(f"{ROSSO}Errore durante il download di {project_id}", end=RESET)
        errored_mods.append(mod)
        continue
    if not response:
        print(f"{ROSSO}Errore: Mod {project_id} non trovata o non disponibile.", end=RESET)
        errored_mods.append(mod)
        continue

    trovato = False
    for _file in response.get("data", []):
        if _file.get("id") == file_id:
            versions = [x.lower() for x in _file.get("gameVersions", [])]
            #print(project_id, versions, end=RESET)
            # Seleziona le mod che non hanno solo client nelle versioni (se ha client e server o se non ha nessuno dei due)
            if "client" in versions and "server" not in versions:
                client_only_mods.append(f"https://www.curseforge.com/api/v1/mods/{project_id}/files/{file_id}/download")
            else:
                server_mods.append((_file.get("fileName", None), f"https://www.curseforge.com/api/v1/mods/{project_id}/files/{file_id}/download", ))
            trovato = True
            break
        
    if not trovato:
        print(f"{ROSSO}Errore: Mod {project_id} non trovata o non disponibile.", end=RESET)
        errored_mods.append(mod)

# Scarica le mod scelte
#print(client_only_mods, end=RESET)
for mod in server_mods:
    name, link = mod
    if not name:
        print(f"{ROSSO}Errore: Mod {link} non ha un nome valido.", end=RESET)
        errored_mods.append(mod)
        continue
    if ".jar" not in response.get("data", [])[0].get("fileName", ""):
        print(f"{ROSSO}Errore: Mod {project_id} non è un file jar.", end=RESET)
        continue
    print(f"{VERDE}Download di {name}...", end=RESET)
    urllib.request.urlretrieve(link, path.join(mods_dir, name))
    #exit(1)
#print(neoforge_link, end=RESET)

# Copia gli override nella cartella del server
if overrides:
    for directory in pathlib.Path(overrides).iterdir():
        if directory.is_dir():
            toignore = False
            for ignored_dir in ignored_dirs:
                if ignored_dir in directory.name:
                    toignore = True
            if not toignore:
                #print(directory, path.join(server_dir, directory.name), end=RESET)
                shutil.copytree(directory, path.join(server_dir, directory.name), dirs_exist_ok=True)