import os
import os.path
import datetime
import zipfile
import tarfile
import logging

logger = logging.getLogger(__name__)

from latexpp.fix import BaseFix


class FnArchive:
    """
    A context manager that provides a simple unified interface for `ZipFile` and
    `TarFile`.
    """
    def __init__(self, basefname, artype):
        self.basefname = basefname
        artypeparts = artype.split('.', maxsplit=1)
        if len(artypeparts) > 1:
            self.artype, self.arcompr = artypeparts
        else:
            self.artype, self.arcompr = artype, None
        self.fname = self.basefname + '.' + self.artype
        if self.arcompr:
            self.fname += '.' + self.arcompr

    def __enter__(self):
        if self.artype == 'zip':
            assert not self.arcompr
            self.f = zipfile.ZipFile(self.fname, "w",
                                     compression=zipfile.ZIP_DEFLATED)

            self.f.__enter__()
            return self
        if self.artype == 'tar':
            self.f = tarfile.open(self.fname, "w:%s"%self.arcompr)
            self.f.__enter__()
            return self

        raise ValueError("Unknown archive type: {}".format(self.artype))
            

    def add_file(self, fname, arfname=None):
        if arfname is None:
            arfname = fname
        logger.debug("%s: Adding %s", os.path.relpath(self.fname), arfname)
        if self.artype == 'zip':
            return self.f.write(fname, arfname)
        elif self.artype == 'tar':
            return self.f.add(fname, arfname)

    def __exit__(self, *args, **kwargs):
        return self.f.__exit__(*args, **kwargs)



class CreateArchive(BaseFix):
    r"""
    Create an archive with all the generated files.

    This rule must be the last rule!

    Arguments:

    - `use_root_dir`: If `True`, then the archive will contain a single
      directory with all the files. The directory name is the same as the output
      directory.  If `False`, then all the files are placed in the archive at
      the root level.

    - `use_date`: If `True`, the current date/time is appended to the archive
      file name.

    - `archive_type`: One of 'zip', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz'.
    """
    def __init__(self, use_root_dir=True, use_date=True, archive_type='zip'):
        super().__init__()
        self.use_root_dir = use_root_dir
        self.use_date = use_date
        self.archive_type = archive_type


    def finalize(self, **kwargs):
        # all set, we can create the archive

        lpp = self.lpp

        arbasename = lpp.output_dir
        if self.use_date:
            arbasename += '-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

        if self.use_root_dir:
            base_dir = os.path.relpath(lpp.output_dir)
        else:
            base_dir = ''
        
        with FnArchive(arbasename, self.archive_type) as far:
            for fn in lpp.output_files:
                far.add_file(os.path.join(lpp.output_dir, fn),
                             os.path.join(base_dir, fn))
            
        logger.info("Created archive %s", os.path.relpath(far.fname))
