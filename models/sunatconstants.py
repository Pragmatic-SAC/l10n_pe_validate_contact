# -*- coding: utf-8 -*-
from enum import Enum


class PersonaNaturalNuevoRusConstant(Enum):
    numero_ruc = 0
    tipo_contribuyente = 1
    nombre_comercial = 3
    fecha_inscripcion = 5
    estado_contribuyente = 7
    condicion_contribuyente = 9
    domicilio_fiscal = 10
    actividad_economica = 11


class PersonaNaturalSinRusConstant(Enum):
    numero_ruc = 0
    tipo_contribuyente = 1
    nombre_comercial = 3
    fecha_inscripcion = 4
    estado_contribuyente = 6
    condicion_contribuyente = 7
    domicilio_fiscal = 8
    actividad_economica = 9


class PersonaJuridicaConstant(Enum):
    numero_ruc = 0
    tipo_contribuyente = 1
    nombre_comercial = 2
    fecha_inscripcion = 3
    estado_contribuyente = 5
    condicion_contribuyente = 6
    domicilio_fiscal = 7
    actividad_economica = 8


class PersonaJuridicaConstantBaja(Enum):
    numero_ruc = 0
    tipo_contribuyente = 1
    nombre_comercial = 2
    fecha_inscripcion = 3
    estado_contribuyente = 5
    condicion_contribuyente = 7
    domicilio_fiscal = 8
    actividad_economica = 9
