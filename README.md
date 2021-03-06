# OpenParty

Cerinta: Media Player capabil sa ruleze fisiere video salvate local si sa functioneze ca un server de stream la un grup conectat de clienti. 
Player-ul va contine o functionalitate de "universal remote" unde orice participant din grup poate sa deruleze, opreasca sau re-porneasca video-ul prin comenzi trimise catre main player. Fiecare player va putea sa isi seteze in particular optiuni cum ar fi subtitrari custom sau volumul.
Orice player client poate deveni la randul lui un server, pornind stream-ul unui alt fisier video local catre grup.

Player-ul va contine si o optiune de text chat si lista participantilor pentru a putea discuta fara a fi necesara o aplicatie externa de comunicare. (optional: functionalitate de webcam si/sau voice chat intre participanti)

Pasi de implementare
1. Functionalitate player video capabil sa ruleze fisiere video salvate local (setare volum/subtitrare numai in sesiunea locala)
2. Metoda de comunicare si streaming a pachetelor cu frame-uri si audio catre clienti (folosind protocol UDP?)
3. Instructiunile play/pause si derularea video-ului din partea clientilor se vor transmite catre player-ul celui care face stream
4. Capabilitatea de a opri primul stream automat atunci cand un client doreste sa devina urmatorul server si sa porneasca stream-ul catre un fisier al lui
5. Functionalitate de chat intre participanti si lista celor activi in sesiune

6[o]. Functionalitate de webcam si/sau voice chat in sesiune <br>
7[o]. Implementare protocol P2P pentru a putea distribui pachetele uniform intre noduri, nu doar de la server la client


Dependente curente: <br>
  player video <br>
    - opencv-contrib-python (libraria de cv2 si numpy incluse) <br>
    - ffpyplayer <br>
    - moviepy <br>

  interfata <br>
    - PyQt (pentru a putea adauga butoane si slider) <br>
    - tkinter <br>
  
  librarii pentru stabilirea conexiunii intre server-clienti <br>
    - <br>
    
    
  -- trebuie cautata o alternativa care sa proceseze video-ul si sa includa interfata de control (de cautat potentiale librarii)
	-- instalat PyQt5
	-- de instalat K-Lite codec pack: http://www.codecguide.com/download_k-lite_codec_pack_full.htm
  
  
  
  Aplicatii similare: <br> 
  [Teleparty](https://www.netflixparty.com/), [Disney Party Plus](https://chrome.google.com/webstore/detail/disney-plus-party/pidpgkcioikhdjahlehighfgmaopdbkk?hl=en) - extensii care permit sincronizarea mai multor participanti pentru acelasi stream de Netflix/Disney Plus (limitat ce ofera libraria serviciilor/fiecare persoana trebuie sa detina un abonament platit) <br>
  [Watch2Gether](https://w2g.tv/?lang=en) - site care permite sincronizarea clipurilor de pe youtube/twitch/vimeo intr-o sesiune comuna <br>
  [Syncplay](https://github.com/Syncplay/syncplay) - extensie pentru playere care permite sincronizarea intre fisierele locale ale participantilor (toti trebuie sa aibe acelasi fisier salvat) <br>
  
  Research de citit: <br>
  [A Review on P2P Video Streaming](https://arxiv.org/ftp/arxiv/papers/1304/1304.1235.pdf) <br>
  [P2P Video Streaming Strategies based on Scalable Video Coding](https://www.elsevier.es/en-revista-journal-applied-research-technology-jart-81-articulo-p2p-video-streaming-strategies-based-S1665642315300109) <br>
  [Protocol de real-time streaming](https://p2psp.org/) <br>
  [PyPPSPP](https://github.com/justas-/PyPPSPP) <br>
  
  [cod curent testat pe PyQt5](https://github.com/baoboa/pyqt5/blob/master/examples/multimediawidgets/player.py) <br>
  
UPDATE (06-06): mutat pe libraria PyQt pentru a genera interfata <br>
		server trimite la client frameuri video si sincronizeaza timestamp-ul si progress bar-ul <br>
		server face host prin TCP pentru chat in care poate primi comenzi de la client pentru a le executa (play/pauza/skipto) <br>
<br>
dependente curente:  <br>
	- opencv-contrib-python 4.5.2.52 --> pentru extras frame-uri din fisier video <br>
	- imutils               0.5.4    --> pentru a face resize la frame-uri <br>
	- PyAudio               0.2.11   --> stream la audio pe chunk-uri <br>
	- PyQt5                 5.15.4 	 --> interfata si QThreads <br>
	- PyQt5-stubs           5.15.2.0 <br>
	- psutil                5.8.0    <br>
	- pycaw                 20181226 --> control volum la nivel de windows API <br>
	- pyinstaller           4.3 	 --> pentru a compila executabile din codul sursa <br>
	<br>
	(una din ele contine designer.exe pentru a contrui fisierele .ui) <br>
	- pyqt5-tools           5.15.4.3.2 <br>
	- qt5-applications      5.15.2.2.2 <br>
	- qt5-tools             5.15.2.1.2 <br>
	<br>
	[extern] <br>
	- ffplayer (pentru server ca sa genereze fisier audio) <br>
	- Radmin VPN (pentru LAN virtual) <br>
fisiere folosite la rulare: "app/server/main_server.py", "app/server/main_client.py" <br>
"pyinstaller --onefile <main_module>.py" ca sa generam executabilele pentru client si server (trebuie copiate fisierele .ui manual in acelasi director) <br>
<br>
> in cazul in care primim o eroare "pyinstaller AttributeError: module 'enum' has no attribute 'IntFlag'" atunci trebuie dezinstalat un modul <br>
> pip uninstall -y enum34 <br>
(probabil a fost instalat de o librarie folosita si nu e compatibil cu python 3.6) <br>
https://stackoverflow.com/questions/43124775/why-python-3-6-1-throws-attributeerror-module-enum-has-no-attribute-intflag <br>
