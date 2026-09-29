"""Tests unitaires pour les transactions atomiques et execute_batch."""

from database import execute_batch, execute_write, query_one, query_rows


def test_execute_batch_success() -> None:
    """Vérifie que plusieurs instructions s'exécutent avec succès en lot."""
    execute_write(
        "CREATE TABLE IF NOT EXISTS _test_batch "
        "(id INTEGER PRIMARY KEY, name TEXT);"
    )
    execute_write("DELETE FROM _test_batch;")

    stmts = [
        ("INSERT INTO _test_batch (id, name) VALUES (?, ?);", [1, "Objet 1"]),
        ("INSERT INTO _test_batch (id, name) VALUES (?, ?);", [2, "Objet 2"]),
        (
            "UPDATE _test_batch SET name = ? WHERE id = ?;",
            ["Objet 1 Modifié", 1],
        ),
    ]
    res = execute_batch(stmts)
    if len(res) != 3:
        raise ValueError(f"Attendu 3 résultats, obtenu {len(res)}")

    rows = query_rows("SELECT * FROM _test_batch ORDER BY id ASC;")
    if len(rows) != 2:
        raise ValueError(f"Attendu 2 lignes, obtenu {len(rows)}")
    if rows[0]["name"] != "Objet 1 Modifié":
        raise ValueError("Nom inattendu sur la première ligne.")
    if rows[1]["name"] != "Objet 2":
        raise ValueError("Nom inattendu sur la deuxième ligne.")

    execute_write("DROP TABLE _test_batch;")
    print("✅ test_execute_batch_success validé !")


def test_execute_batch_rollback_on_failure() -> None:
    """Vérifie qu'une transaction atomique annule TOUT si une requête échoue."""
    execute_write(
        "CREATE TABLE IF NOT EXISTS _test_rollback "
        "(id INTEGER PRIMARY KEY, name TEXT UNIQUE);"
    )
    execute_write("DELETE FROM _test_rollback;")
    execute_write(
        "INSERT INTO _test_rollback (id, name) VALUES (1, 'Existant');"
    )

    # Lot contenant une violation de contrainte d'unicité (id=1 existe déjà)
    failing_stmts = [
        (
            "INSERT INTO _test_rollback (id, name) VALUES (?, ?);",
            [2, "Nouveau temporaire"],
        ),
        (
            "INSERT INTO _test_rollback (id, name) VALUES (?, ?);",
            [1, "Doublon Erreur"],
        ),
    ]

    failed = False
    try:
        execute_batch(failing_stmts)
    except Exception:
        failed = True

    if not failed:
        raise ValueError("La transaction aurait dû lever une exception !")

    # Vérification du rollback : l'élément 2 NE DOIT PAS être en base
    count_row = query_one("SELECT COUNT(*) as c FROM _test_rollback;")
    if not count_row or count_row["c"] != 1:
        cnt = count_row["c"] if count_row else 0
        raise ValueError(
            f"Rollback échoué : {cnt} éléments trouvés au lieu de 1 !"
        )

    row2 = query_one("SELECT * FROM _test_rollback WHERE id = 2;")
    if row2 is not None:
        raise ValueError(
            "L'élément inséré avant l'erreur n'a pas été rollbacké !"
        )

    execute_write("DROP TABLE _test_rollback;")
    print("✅ test_execute_batch_rollback_on_failure validé !")


if __name__ == "__main__":
    test_execute_batch_success()
    test_execute_batch_rollback_on_failure()
    print("\n🎉 TOUS LES TESTS DE TRANSACTIONS SONT VALIDÉS !")
