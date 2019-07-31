import os
import os.path
import datetime
import shutil
import logging

logger = logging.getLogger(__name__)

from latexpp.fixes import BaseFix


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

    - `archive_type`: One of 'zip', 'tar', 'gztar', 'bztar', 'xztar'.
    """
    def __init__(self, use_root_dir=True, use_date=True, archive_type='zip'):
        self.use_root_dir = use_root_dir
        self.use_date = use_date
        self.archive_type = archive_type


    def finalize(self, lpp, **kwargs):
        # all set, we can create the archive

        zipname = lpp.output_dir
        if self.use_date:
            zipname += '-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

        if self.use_root_dir:
            root_dir = '.'
        else:
            root_dir = lpp.output_dir

        arname = shutil.make_archive(
            zipname,
            self.archive_type, # eg., 'zip'
            root_dir=root_dir,
            base_dir=os.path.relpath(lpp.output_dir),
            logger=logger
        )
        logger.info("Create archive %s", arname)
