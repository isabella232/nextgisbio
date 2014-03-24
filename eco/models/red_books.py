# encoding: utf-8

import csv

from sqlalchemy import Table, Column, Integer, String, Enum, Text, ForeignKey, Sequence, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy import func

from eco.models import DBSession, Base, Taxon
from eco.utils.jsonify import JsonifyMixin

import transaction


class RedBook(Base, JsonifyMixin):
    __tablename__ = 'red_books'

    id = Column(Integer, Sequence('red_books_id_seq', start=1), primary_key=True)
    name = Column(String, nullable=False, unique=True)

    @staticmethod
    def import_from_csv(path_to_file):
        session = DBSession()

        log = {
            'not_found': [],
            'duplicates': []
        }

        reader = csv.reader(open(path_to_file), delimiter='\t')
        reader.next()
        records = [line for line in reader]
        red_books = {}
        for region, orig_name, lat_name, population, status, univ_status, year, bibl in records:
            if bibl in red_books:
                continue
            else:
                red_books[bibl] = True

        with transaction.manager:
            for red_book_name in red_books.keys():
                red_book = RedBook(
                    name=red_book_name
                )
                session.add(red_book)

        red_books_db = session.query(RedBook).all()
        red_books = {}
        for red_book_db in red_books_db:
            red_books[red_book_db.name.encode('utf8')] = red_book_db.id

        with transaction.manager:
            for region, orig_name, lat_name, population, status, univ_status, year, bibl in records:

                taxons = session.query(Taxon).filter_by(name=lat_name).all()
                taxon_id = None

                if len(taxons) == 1:
                    taxon_id = taxons[0].id
                else:
                    log['not_found'].append(orig_name)
                    continue

                red_book_id = red_books[bibl]

                count = session.query(func.count(RedBookSpecies.specie_id))\
                    .filter(RedBookSpecies.red_book_id == red_book_id)\
                    .filter(RedBookSpecies.specie_id == taxon_id).scalar()

                if count > 0:
                    log['duplicates'].append(taxons[0].name)
                    continue

                red_book_specie = RedBookSpecies(
                    red_book_id=red_book_id,
                    specie_id=taxon_id,
                    population=population,
                    status=status,
                    univ_status=univ_status,
                    year=int(year) if year else None,
                    region=region
                )

                session.add(red_book_specie)
                session.flush()

        print '\n\rNOT FOUND:\n\r{0}'.format('\n\r'.join(log['not_found']))
        print '\n\rDUPLICATES:\n\r{0}'.format('\n\r'.join(log['duplicates']))


class RedBookSpecies(Base, JsonifyMixin):
    __tablename__ = 'red_books_species'

    red_book_id = Column(Integer, ForeignKey('red_books.id'), primary_key=True)
    specie_id = Column(Integer, ForeignKey('taxon.id'), primary_key=True)
    population = Column(Text)
    status = Column(Text, index=True)
    univ_status = Column(Text, index=True)
    year = Column(Integer, index=True)
    region = Column(Text)
    taxon = relationship("Taxon")