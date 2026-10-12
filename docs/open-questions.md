# Points non résolus et questions ouvertes

Ce document consigne toutes les questions, hypothèses et points de doute conformément au §8 de `AGENTS.md`.

---

## 1. Format INI (`.picasa.ini` / `Picasa.ini`)
*Statut : Résolu & validé par tests round-trip.*

- [x] Localisation exacte des fonctions de parsing et de sérialisation INI dans `Picasa3.exe` :
  - Writer : `FUN_0068ac80` @ `0x0068AC80` - `0x0068C412`.
  - Reader/Parser : `FUN_009be730` @ `0x009BE730`, `FUN_009bd390` @ `0x009BD390`.
- [x] Encodage exact : UTF-8 sans BOM, fins de ligne strictly CRLF (`\r\n`).
- [x] Comportement en lecture : recherche de section délimitée par `[` et `]`, recherche de clé suivie de `=`, comparaison insensible à la casse ASCII (+0x20).
- [x] Préservation intégrale des lignes inconnues, commentaires et espacements lors du round-trip.

---

## 2. Format PMP (`.pmp` - Base de données colonne)
*Statut : Résolu & validé par tests round-trip.*

- [x] Localisation dans le binaire : `CPropertyMap` (`.\thumblab\CPropertyMap.cpp` @ `0x00CA8104`), `FUN_006a2b60`, `FUN_006d17f0`.
- [x] Structure de l'en-tête (20 octets) :
  - `magic` = `0x3FCCCCCD` (float 1.6f).
  - `type_id` = `0x13320000 | type_enum`.
  - `subversion` = `0x00000002`.
  - `type_id_repeat` = `type_id`.
  - `record_count` = nombre de lignes.
- [x] Types de données identifiés et validés (0x0000 à 0x0007).
- [x] Validé à 100% sur l'intégralité des 56 fichiers réels de `AppData/Local/Google/Picasa2/db3`.

---

## 3. Autres fichiers de base de données (`db3/`)
*Statut : Prochaine étape.*

- [ ] Structure des fichiers `.db` d'index et de miniatures (`thumbs_0.db`, `thumbs_index.db`, `albums_0.db`).
- [ ] Format des fichiers `.dat` (`repository.dat`, `usernames.dat`, `wordhash.dat`).
