from datetime import datetime

def format_period(start_date: str, end_date: str) -> str:
    try:
        start = datetime.strptime(start_date, "%H:%M")
        end = datetime.strptime(end_date, "%H:%M")

        if end <= start:
            raise ValueError("A hora de fim deve ser posterior a hora de inicio.")

        return f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
    except ValueError as ex:
        raise ValueError(f"Erro ao formatar período: {ex}")