from src.contrato import Momento


def test_momento_a_partir_de_hora_minuto_e_segundo():
    assert Momento.de_horario(3, 6, 1, 5) == Momento(3, 6 * 3600 + 65)


def test_horario_formatado_com_dois_digitos():
    assert Momento.de_horario(1, 6).horario == "06:00:00"
    assert Momento.de_horario(1, 18, 59, 59).horario == "18:59:59"


def test_apos_avanca_segundos_no_mesmo_dia():
    assert Momento.de_horario(2, 8, 59, 30).apos(45) == Momento.de_horario(2, 9, 0, 15)


def test_momentos_sao_ordenados_por_dia_e_depois_por_horario():
    assert Momento.de_horario(1, 18) < Momento.de_horario(2, 6)
    assert Momento.de_horario(2, 6) < Momento.de_horario(2, 6, 0, 1)
