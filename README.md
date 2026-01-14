# 🍎 macOS Multiboot Tool

Outil Python pour créer une clé USB multiboot permettant d'installer plusieurs versions de macOS sur un seul disque externe.

## 📋 Ce que fait le script

Le script automatise la création d'une clé USB multiboot en :
- Détectant automatiquement les installateurs macOS dans `/Applications`
- Partitionnant le disque externe (un volume par version de macOS)
- Créant les médias d'installation bootables sur chaque partition

## 🚀 Démarrage rapide

### Prérequis
- **macOS** (le script utilise `diskutil`)
- Python 3.6+
- Installateurs macOS dans `/Applications` (téléchargeables via [Mist](https://github.com/ninxsoft/Mist))
- Un disque externe avec suffisamment d'espace
- **Privilèges administrateur** (sudo requis)

### Utilisation

1. Connectez votre disque externe
2. Lancez le script :
```bash
sudo python3 main.py
```

3. Le script vous guidera pour :
   - Sélectionner le disque cible
   - Confirmer l'effacement du disque
   - Créer automatiquement les partitions et installer chaque version

### Options

- Mode debug (logs détaillés)
```bash
sudo python3 main.py --debug
```
- Spécifier un autre répertoire pour les installateurs
```bash
sudo python3 main.py --app-dir /chemin/vers/installateurs
```

## ⚠️ Avertissement important

**Le disque sélectionné sera COMPLÈTEMENT EFFACÉ.** Sauvegardez toutes vos données importantes avant de continuer.

## 📥 Télécharger les installateurs

1. Téléchargez [Mist](https://github.com/ninxsoft/Mist/releases)
2. **Choisissez "Installer" (pas "Firmware")** et format **"Application (.app)"**
3. Sélectionnez la version de macOS souhaitée
4. Déplacez le fichier `.app` téléchargé dans `/Applications`

## 🐛 Problèmes courants

- **Aucun installateur trouvé** : Vérifiez qu'ils sont dans `/Applications` au format `.app`
- **Permission refusée** : Assurez-vous d'utiliser `sudo`
- **Aucun disque externe** : Vérifiez que le disque est connecté, monté et dispose de suffisamment d'espace libre

---

*Développé avec ❤️ par [SAWKIT](https://github.com/gitsawkit)*
