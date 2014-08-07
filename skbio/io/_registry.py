from .util import open_file, _get_filehandle
from skbio.io import (FormatIdentificationError, FileFormatError,
                      DuplicateRegistrationError)
_formats = {}
_identifiers = {}


def register_identifier(fmt):
    """Return a decorator for an identifier function.

    A decorator factory for identifier functions.

    An identifier function should have at least the following signature:
    ``<format_name>_identifier(fh)``. `fh` is an open fileobject.

    **The idientifier must not close the fileobject** `fh`, cleanup must be
    handled external to the identifier and is not it's concern.

    Any additional `*args` and `**kwargs` will be passed to the identifier and
    may be used if necessary.

    The identifier **must** return an True if it believes `fh` is a given
    `fmt`. Otherwise it should return False.

    The identifier may determine membership of a file in as many or as few
    lines of the file as it deems necessary.

    Parameters
    ----------
    fmt : str
        A format name which a decorated identifier will be bound to.

    Returns
    -------
    function
        A decorator to be used on a identifer. The decorator will raise a
        ``skbio.io.DuplicateRegistrationError`` if there already exists an
        *identifier* bound to the `fmt`.

    Note
    -----
        Failure to adhere to the above interface specified for an identifier
        will result in unintended side-effects.

        The returned decorator does not mutate the decorated function in any
        way, it only adds the function to a global registry for use with
        ``skbio.io.guess_format``

    See Also
    --------
    skbio.io.guess_format

    """
    def decorator(identifier):
        if fmt in _identifiers:
            raise DuplicateRegistrationError("'%s' already has an identifier."
                                             % fmt)
        _identifiers[fmt] = identifier
        return identifier
    return decorator


def register_reader(fmt, *cls):
    """Return a decorator for a reader function.

    A decorator factory for reader functions.

    A reader function should have at least the following signature:
    ``<format_name>_to_<class_name_or_generator>(fh)``. `fh` is an open
    fileobject.

    **The reader must not close the fileobject** `fh`, cleanup must be handled
    external to the reader and is not it's concern.

    Any additional `*args` and `**kwargs` will be passed to the reader and may
    be used if necessary.

    The reader **must** return an instance of `cls` if `cls` is not None.
    Otherwise the reader must return a generator. The generator need not deal
    with closing the `fh` this is the responsibility of the caller and is
    handled for you in ``skbio.io.read``.


    Parameters
    ----------
    fmt : str
        A format name which a decorated reader will be bound to.
    cls : type, optional
        Positional argument.
        The class which a decorated reader will be bound to. If not provided
        or is None, the decorated reader will be bound as a generator.
        Default is None.

    Returns
    -------
    function
        A decorator to be used on a reader. The decorator will raise a
        ``skbio.io.DuplicateRegistrationError`` if there already exists a
        *reader* bound to the same permutation of `fmt` and `cls`.

    Raises
    ------
    TypeError

    Note
    -----
        Failure to adhere to the above interface specified for a reader will
        result in unintended side-effects.

        The returned decorator does not mutate the decorated function in any
        way, it only adds the function to a global registry for use with
        ``skbio.io.read``

    See Also
    --------
    skbio.io.read

    """
    return _rw_decorator('reader', fmt, *cls)


def register_writer(fmt, *cls):
    """Return a decorator for a writer function.

    A decorator factory for writer functions.

    A writer function should have at least the following signature:
    ``<class_name_or_generator>_to_<format_name>(obj, fh)`` where `obj` will
    be either an instance of <class_name> or a generator that is *identical* to
    the result of calling ``get_reader(<format>, None)``. `fh` is an open
    fileobject.

    **The writer must not close the fileobject** `fh`, cleanup must be handled
    external to the writer and is not it's concern.

    Any additional `*args` and `**kwargs` will be passed to the writer and may
    be used if necessary.

    The writer must not return a value. Instead it should only mutate the `fh`
    in a way consistent with it's purpose.

    If the writer accepts a generator, it should exhaust the generator to
    ensure that the potentially open fileobject backing said generator is
    closed.

    Parameters
    ----------
    fmt : str
        A format name which a decorated writer will be bound to.
    cls : type, optional
        Positional argument.
        The class which a decorated writer will be bound to. If not provided
        or is None, the decorated writer will be bound as a generator.
        Default is None.

    Returns
    -------
    function
        A decorator to be used on a writer. The decorator will raise a
        ``skbio.io.DuplicateRegistrationError`` if there already exists a
        *writer* bound to the same permutation of `fmt` and `cls`.

    Raises
    ------
    TypeError

    Note
    -----
        Failure to adhere to the above interface specified for a writer will
        result in unintended side-effects.

        The returned decorator does not mutate the decorated function in any
        way, it only adds the function to a global registry for use with
        ``skbio.io.write``

    See Also
    --------
    skbio.io.write

    """
    return _rw_decorator('writer', fmt, *cls)


def _rw_decorator(name, fmt, *args):
    cls = None
    arg_len = len(args)
    if arg_len > 1:
        raise TypeError("register_%s takes 1 or 2 arguments (%d given)"
                        % (name, arg_len))
    if arg_len == 1:
        cls = args[0]

    def decorator(func):
        if fmt not in _formats:
            _formats[fmt] = {}
        format_dict = _formats[fmt]
        if cls not in format_dict:
            format_dict[cls] = {}
        format_class = format_dict[cls]
        if name not in format_class:
            format_class[name] = func
        else:
            raise DuplicateRegistrationError("'%s' already has a %s for %s."
                                             % (fmt, name, cls.__name__))

        return func
    return decorator


def list_read_formats(cls):
    """Return a list of available read formats for a given `cls` type.

    Parameters
    ----------
    cls : type
        The class which will be used to determine what read formats exist for
        an instance of `cls`.

    Returns
    -------
    list
        A list of available read formats for an instance of `cls`. List may be
        empty.

    See Also
    --------
    skbio.io.register_reader

    """
    return _rw_list_formats('reader', cls)


def list_write_formats(cls):
    """Return a list of available write formats for a given `cls` instance.

    Parameters
    ----------
    cls : type
        The class which will be used to determine what write formats exist for
        an instance of `cls`.

    Returns
    -------
    list
        A list of available write formats for an instance of `cls`. List may be
        empty.

    See Also
    --------
    skbio.io.register_writer

    """
    return _rw_list_formats('writer', cls)


def _rw_list_formats(name, cls):
    formats = []
    for fmt in _formats:
        if cls in _formats[fmt]:
            if name in _formats[fmt][cls]:
                formats.append(fmt)
    return formats


def get_identifier(fmt):
    """Return an identifier for a format.

    Parameters
    ----------
    fmt : str
        A format string which has a registered identifier.

    Returns
    -------
    function or None
        Returns an identifier function if one exists for the given `fmt`.
        Otherwise it will return None.

    See Also
    --------
    skbio.io.register_identifier

    """

    if fmt in _identifiers:
        return _identifiers[fmt]
    return None


def get_reader(fmt, *cls):
    """Return a reader for a format.

    Parameters
    ----------
    fmt : str
        A registered format string.
    cls : type, optional
        Positional argument.
        The class which the reader will return an instance of. If not provided
        or is None, the reader will return a generator.
        Default is None.

    Returns
    -------
    function or None
        Returns a reader function if one exists for a given `fmt` and `cls`.
        Otherwise it will return None.

    See Also
    --------
    skbio.io.register_reader

    """

    return _rw_getter('reader', fmt, *cls)


def get_writer(fmt, *cls):
    """Return a writer for a format.

    Parameters
    ----------
    fmt : str
        A registered format string.
    cls : type, optional
        Positional argument.
        The class which the writer will expect an instance of. If not provided
        or is None, the writer will expect a generator that identical to what
        is returned by ``get_reader(<some_format>, None)``.
        Default is None.

    Returns
    -------
    function or None
        Returns a writer function if one exists for a given `fmt` and `cls`.
        Otherwise it will return None.

    See Also
    --------
    skbio.io.register_writer

    """

    return _rw_getter('writer', fmt, *cls)


def _rw_getter(name, fmt, *args):
    cls = None
    arg_len = len(args)
    if arg_len > 1:
        raise TypeError("get_%s takes 1 or 2 arguments (%d given)"
                        % (name, arg_len))
    if arg_len == 1:
        cls = args[0]

    if fmt in _formats:
        if cls in _formats[fmt]:
            if name in _formats[fmt][cls]:
                return _formats[fmt][cls][name]
    return None


def guess_format(fp, cls=None):
    """Attempt to guess the format of a file and return format str.

    Parameters
    ----------
    fp : filepath or fileobject
        The provided file to guess the format of. Filepaths are automatically
        closed; fileobjects are the responsibility of the caller.
    cls : type, optional
        A provided class that restricts the search for the format. Only formats
        which have a registered reader or writer for the given `cls` will be
        tested.
        Default is None.

    Returns
    -------
    str
        A registered format name.

    Raises
    ------
    FormatIdentificationError

    Note
    -----
        If a fileobject is provided, the current read offset will be reset.

        If the file is 'claimed' by multiple identifiers, or no identifier
        'claims' the file, an ``skbio.io.FormatIdentificationError`` will be
        raised.

    See Also
    --------
    skbio.io.register_identifier

    """
    with open_file(fp, 'U') as fh:
        possibles = []
        fh.seek(0)
        for fmt in _identifiers:
            if cls is not None and (fmt not in _formats or
                                    cls not in _formats[fmt]):
                continue
            test = _identifiers[fmt]
            if test(fh):
                possibles.append(fmt)
            fh.seek(0)
        if not possibles:
            raise FormatIdentificationError("Cannot guess the format for %s."
                                            % str(fh))
        if len(possibles) > 1:
            raise FormatIdentificationError("File format is ambiguous, may be"
                                            " one of %s." % str(possibles))

        return possibles[0]


def read(fp, format=None, into=None, mode='U', *args, **kwargs):
    """Generalized read function: multiplex read functionality in skbio.

    This function is able to reference and execute all *registered* read
    operations in skbio.

    Parameters
    ----------
    fp : filepath or fileobject
        The location to read the given `format` `into`. Filepaths are
        automatically closed when read; fileobjects are the responsibility
        of the caller. In the case of a generator, a filepath will be closed
        when ``StopIteration`` is raised; fileobjects are still the
        responsibility of the caller.
    format : str, optional
        The format must be a reigstered format name with a reader for the given
        `into` class. If a `format` is not provided or is None, all registered
        identifiers for the provied `into` class will be evaluated to attempt
        to guess the format. Will raise an
        ``skbio.io.FormatIdentificationError`` if it is unable to guess.
        Default is None.
    into : type, optional
        A class which has a registered reader for a given `format`. If `into`
        is not provided or is None, read will return a generator.
        Default is None.
    mode : str, optional
        The read mode. This is passed to `open(fp, mode)` internally.
        Default is 'U'.
    args : tuple, optional
        Will be passed directly to the appropriate reader.
    kwargs : dict, optional
        Will be passed directly to the appropriate reader.

    Returns
    -------
    object or generator
        If `into` is not None, an instance of the `into` class will be
        provided with internal state consistent with the provided file.
        If `into` is None, a generator will be returned.

    Raises
    ------
    ValueError
    skbio.io.FileFormatError
    skbio.io.FormatIdentificationError

    Note
    -----
        Will raise a ``ValueError`` if `format` and `into` are both be None.

    See Also
    --------
    skbio.io.register_writer
    skbio.io.register_identifier

    """
    if format is None and into is None:
        raise ValueError("`format` and `into` cannot both be None.")

    fh, is_own = _get_filehandle(fp, mode)

    if format is None:
        format = guess_format(fh, cls=into)

    reader = get_reader(format, into)
    if reader is None:
        raise FileFormatError("Cannot read %s into %s, no reader found."
                              % (format, into.__name__
                                 if into is not None
                                 else 'generator'))

    if into is None:
        def wrapper_generator():
            original = reader(fh, *args, **kwargs)
            try:
                while(True):
                    yield next(original)
            finally:
                if is_own:
                    fh.close()

        return wrapper_generator()

    else:
        result = reader(fh, *args, **kwargs)
        if is_own:
            fh.close()

        return result


def write(obj, format=None, into=None, mode='w', *args, **kwargs):
    """Generalized write function: multiplex write functionality in skbio.

    This function is able to reference and execute all *registered* write
    operations in skbio.

    Parameters
    ----------
    obj : object
        The object must have a registered writer for a provided `format`.
    format : str
        The format must be a reigstered format name with a writer for the given
        `obj`
    into : filepath or fileobject
        The location to write the given `format` from `obj` into. Filepaths are
        automatically closed when written; fileobjects are the responsibility
        of the caller.
    mode : str, optional
        The write mode. This is passed to `open(fp, mode)` internally.
        Default is 'w'.
    args : tuple, optional
        Will be passed directly to the appropriate writer.
    kwargs : dict, optional
        Will be passed directly to the appropriate writer.

    Raises
    ------
    ValueError
    skbio.io.FileFormatError

    See Also
    --------
    skbio.io.register_writer

    """
    if format is None:
        raise ValueError("Must specify a `format` to write out as.")
    if into is None:
        raise ValueError("Must provide a filepath or filehandle for `into`")

    with open_file(into, mode) as fh:
        writer = get_writer(format, obj.__class__)
        if writer is None:
            raise FileFormatError("Cannot write %s into %s, no writer found."
                                  % (format, str(fh)))

        writer(obj, fh, *args, **kwargs)
