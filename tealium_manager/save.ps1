# --- CONFIGURATION ---
$BASE_DIR = "."
$BRANCH = "release-3"

Write-Host "--- Preparation de l'envoi ---"

# 1. Verification dossier
Set-Location $BASE_DIR

# 2. Verifier changements
$status = git status --porcelain
if (-not $status) {
    Write-Host "Rien a envoyer"
    exit
}

# 3. Message de commit
Write-Host "Message de commit (Entree pour auto) :"
$userMessage = Read-Host

if (-not $userMessage) {
    $userMessage = "Update auto"
}

# 4. Execution Git
Write-Host "Envoi en cours..."

git add .
git commit -m "$userMessage"
git push origin $BRANCH

# 5. Resultat
if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCES"
} else {
    Write-Host "ERREUR"
}

Write-Host "Appuie sur Entree pour fermer"
Read-Host