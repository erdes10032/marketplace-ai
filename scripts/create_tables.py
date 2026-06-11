import argparse



from _bootstrap import bootstrap



bootstrap()



from app.database import get_engine

from app.models import Base





def main() -> None:

    parser = argparse.ArgumentParser(description="Создание схемы PostgreSQL")

    parser.add_argument(

        "--force-recreate",

        action="store_true",

        help="Удалить все таблицы и создать заново (все данные будут потеряны)",

    )

    args = parser.parse_args()



    engine = get_engine()

    if args.force_recreate:

        Base.metadata.drop_all(bind=engine)

        print("Existing tables dropped.")



    Base.metadata.create_all(bind=engine)

    print("Database schema ready.")





if __name__ == "__main__":

    main()

