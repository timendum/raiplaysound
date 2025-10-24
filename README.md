# RaiPlaySound - Podcast non ufficiale

Questa pagina è solo per chi vuole smanettare, altrimenti il lavoro è già fatto. In ogni caso...

## Vai su http://timendum.github.io/raiplaysound/

### FAQ

#### Non trovo il programma che mi interessa

Dall'elenco generato e disponibile [qui](https://timendum.github.io/raiplaysound/),
sono esclusi i programmi quotidiani e le audiodescrizioni dei film.

Controlla se quello che ti interessa rientra in questa categoria.  
In caso positivo, questo software funziona comunque,
puoi installarlo ed ottenere il programma che ti interessa seguendo
le istruzioni in [questa sezione](https://timendum.github.io/raiplaysound/#diy).

#### Dal podcast mancano gli ultimi episodi

Aggiorno i podcast ogni tanto, se sono passati vari mesi, apri pure una issue.

Se hai fretta o vuoi un podcast sempre aggiornato,
il consiglio è quello di [fare da solo](https://timendum.github.io/raiplaysound/#diy).

#### Ho fatto girare il software, ma la mia lista è più piccola

Capita, ogni tanto dal sito scompaiono dei programmi e quindi il software non li estrae più.

Io faccio girare il software dove ho i file dell'esecuzione precedente,
in modo da mantenere i singoli file di podcast (anche se non più aggiornati).

## Uso: comandi CLI

Questo progetto fornisce un'interfaccia a riga di comando chiamata `raiplaysound`.

Per usare la CLI eseguire il modulo come script oppure installare il pacchetto e l'eseguibile `raiplaysound`:

Esempio rapido (con uv):

```bash
uvx raiplaysound
```

In alternativa puoi fare checkout del progetto (o di un fork)
ed eseguire con

```bash
python -m raiplaysound
```

### Comando: `single`

Genera un file RSS a partire da una singola url di un programma, podcast o playlist di RaiPlaySound.

Esecuzione: `uvx raiplaysound single <url> [opzioni]`

Argomenti e opzioni:

- url (obbligatorio): URL del podcast o della playlist su raiplaysound (es. `https://www.raiplaysound.it/programma/xyz`).
- -f, --folder (default: `.`): cartella in cui scrivere il file XML del podcast.
- --skip <tipo>: specifica una o più tipologie da saltare o includere (vedi sotto).
- --dateok: lascia inalterata la data di pubblicazione degli episodi (se presente nei dati).
- --reverse: ordina gli episodi dal più recente al meno recente (reverse order).

Esempio:

```bash
python -m raiplaysound single https://www.raiplaysound.it/programma/mio-podcast --folder out --skip default --dateok
```

Nota: il comando salva il feed in formato RSS in `folder/<nome>.xml` dove `<nome>` è ricavato dall'URL.

### Comando: all

Scansiona l'indice di RaiPlaySound e genera un feed RSS per ogni programma trovato.

Esecuzione: `uvx raiplaysound all [opzioni]`

Opzioni:

- --skip <tipo>: consente di impostare le tipologie da saltare o usare 'default' per il comportamento predefinito.
  Esempi: `--skip default` (usa i tipi predefiniti), `--skip film --skip "programmi radio"`.
- --workers N (default: 1): numero di worker in parallelo da usare per generare i feed. Se `N` è maggiore di 1 viene usata la modalità multithread.

Esempio:

```bash
python -m raiplaysound all --workers 8
```

I feed generati sono salvati nella cartella `out` del progetto.

### Comando: index

Genera una pagina `index.html` (basata su `index.template`) che elenca tutti i feed RSS già generati nella cartella `out`.

Esecuzione: `uvx raiplaysound index`

Questo comando non accetta opzioni aggiuntive. Produce `out/index.html` leggendo tutti i file `*.xml` presenti in `out`.
