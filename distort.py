from wand.color import Color
from wand.image import Image
import magic
import ffmpeg
import os


class DeeStorter():
    """This class represents the distortion functions for images, videos and gifs
    
    Args:
        :param filespath: files to be distorted (auto-clean by script when job is done)
        :param frames_path: path with disassembled frames from video/gif (auto-clean by script when job is done)
        :param distorted_frames_path: path with distorted frames (auto-clean by script when job is done)
        :param edited_files_path: output files
    
    """

    def __init__(self, filespath: str, frames_path:str, distorted_frames_path: str, edited_files_path: str):
        self.filespath = filespath
        self.frames_path = frames_path
        self.distorted_frames_path = distorted_frames_path
        self.edited_files_path = edited_files_path
        self.mime = magic.Magic(mime=True)

    def distort(self, filename: str, rescale_rate = 1.7) -> str:
        """Main function that distorts everything you want

        Args:
            :param filename: str param of filename (include extension)
            :param rescale_rate: float param (1 and more) that 1 is minimum rescale and about 2.5 is a full rescale
            NOTE that if you trying to distort video/gif, this parameter will be used as start value

        Example: 
            Video/gif with rescale_rate = 1.7 will be rescaled at first frame with 1.7 and every percent 
            of timeline will be increased by value that depends on current percentage of timeline
            End frame will be always no more than rescale_rate + 1

        More on http://docs.wand-py.org/en/0.4.1/wand/image.html?highlight=liquid#wand.image.BaseImage.liquid_rescale
        """

        if filename in os.listdir(f'{self.filespath}'):
            mtype = (self.mime.from_file(f"{self.filespath}{filename}")).split('/')

        else:
            raise FileNotFoundError
        
        # checks mime type
        if mtype[1] == 'gif':
            return self.distort_video(filename, rescale_rate, 'gif')

        elif mtype[0] == 'video':
            return self.distort_video(filename, rescale_rate, 'video')

        elif mtype[0] == 'image':
            return self.distort_image(filename, rescale_rate)

        else:
            raise Exception('This kind of file can not be distorted')

    def distort_image(self, filename: str, rescale_rate: float) -> str:
        img = Image(filename=f'{self.filespath}{filename}')
        x, y = img.size[0], img.size[1]
        img.liquid_rescale(int(x // rescale_rate), int(y // rescale_rate), delta_x=1, rigidity=0)
        img.transform(f'{x}x{y}', '200%')
        img.save(filename=f'{self.edited_files_path}{filename}')
        os.remove(f'{self.filespath}{filename}')
        return filename
        
    def distort_video(self, filename: str, rescale_rate: float, ctype: str) -> str:
        """Function that distort video/gif

        Args:
            :param filename: full filename with extension
            :param rescale_rate: see main function docs
            :param ctype: accepts only two values (video or gif). That needs to assemble gifs without audio

        Function clean all of extracted and distorted frames in dirs
        
        Returns:
            :filename str
        """
        probe = ffmpeg.probe(f'{self.filespath}{filename}')
        origin_w, origin_h = probe['streams'][0]['width'], probe['streams'][0]['height']
        stream = ffmpeg.input(f'{self.filespath}{filename}')

        # disassemble video to jpegs
        (
            ffmpeg
            .output(stream, '{}jpg%04d.jpg'.format(self.frames_path))
            .run()
        )
        
        # frame counters
        cur_frame = 1
        frames_count = int(probe['streams'][0]['nb_frames'])

        # distort every extracted frame
        for file in sorted(os.listdir(f'{self.frames_path}')):
            # set rescale that depends on current timeline percentage
            cur_rescale = round((cur_frame / frames_count + rescale_rate), 2) 

            img = Image(filename=f'{self.frames_path}{file}')
            x, y = img.size[0], img.size[1]
            img.liquid_rescale(int(x // cur_rescale), int(y // cur_rescale), delta_x=1, rigidity=0)
            img.transform(f'{x}x{y}', '200%')
            img.save(filename=f'{self.distorted_frames_path}{file}')
            cur_frame += 1
        try:
            if ctype == 'video':
                distorted_audio = stream.audio.filter('tremolo', f=5.0, d=0.1).filter('vibrato', f=5.0, d=0.1)
                
                (
                    ffmpeg
                    .input('{}jpg%04d.jpg'.format(self.distorted_frames_path))
                    .filter('scale', width=origin_w, height=origin_h)
                    .output(distorted_audio, f'{self.edited_files_path}{filename}.mp4', acodec='aac')
                    .run()
                )
            else:
                (
                    ffmpeg
                    .input('{}jpg%04d.jpg'.format(self.distorted_frames_path))
                    .filter('scale', width=origin_w, height=origin_h)
                    .output(f'{self.edited_files_path}{filename}.mp4')
                    .run()
                )
            os.remove(f'{self.filespath}{filename}')

        except Exception:
            raise Exception

        finally:
            self.cleaner()
            return filename


    def cleaner(self):
        for file in os.listdir(f'{self.frames_path}'):
            os.remove(f'{self.frames_path}{file}')
        for file in os.listdir(f'{self.distorted_frames_path}'):
            os.remove(f'{self.distorted_frames_path}{file}')