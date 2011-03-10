"""
    InterpoList module (c) Gaz Davidson December 2009.

    This is a simple interpolated list type useful for graphing, you
    can set values at any index and it will linearly interpolate between
    the missing ones.

    License:
       Use for any purpose under one condition: I am not to blame for anything.
"""

from bisect import bisect, bisect_left
from math import fabs
import string

class InterpoList(object):
    """
        A list type which automatically does linear interpolation.
        For example:
            >>> a = InterpoList()
            >>> a[0]   = 0
            >>> a[100] = 200
            >>> a[200] = 0
            >>> a[50]
            100.0
            >>> a[125]
            150.0
    """
    def __init__(self, data = {}):
        """ constructor """
        self.items = data.items()
        self.items.sort()

    def __getitem__(self, index):
        """ Returns the value for a given index """
        # handle slices
        if isinstance(index, slice):
            if not index.start: index = slice(self.items[0][0], index.stop, index.step)
            if not index.stop: index = slice(index.start, self.items[-1][0], index.step)
            if index.step:
                # return requested points
                return [self[x] for x in range(index.start, index.stop, index.step)]
            else:
                # if no step/stride given, return ends and set of points in between
                i = bisect(self.items, (float(index.start),0))
                j = bisect(self.items, (float(index.stop),0))
                body = [float(x[1]) for x in self.items[int(i+1):int(j)]]
                return [self[index.start]] + body
        # create a dummy item for searching
        findex = float(index)
        item   = (findex, 0)
        # find the position where it would be inserted
        i = bisect(self.items, item)

        # TODO make extrapolation optional
        if i == 0:
            return self.items[0][1]
	if i == len(self.items):
	    return self.items[i-1][1]

        if i == 0 and self.items[0][0] != findex: # or i > len(self.items):
            # refuse to extrapolate
            raise IndexError("Extrapolation is not supported")
        else:
            if self.items[i-1][0] == findex:
                # exact
                return self.items[i-1][1]
            else:
                if i == len(self.items):
                    # refuse to extrapolate
                    raise IndexError("Extrapolation is not supported")
                else:
                    # interpolate                    
                    factor = (self.items[i][0] - findex) / (self.items[i][0] - self.items[i-1][0])
                    return self.items[i][1] - (self.items[i][1] - self.items[i-1][1])*factor

    def __setitem__(self, key, value):
        """ adds a new keypoint or replaces a current one """
        # create a new list item
        fkey = float(key)
        item = (fkey, value)
        # find the insertion point
        i = bisect_left(self.items, item)
        
        # replace existing value?
        if i < len(self.items) and self.items[i][0] == fkey:
            self.items[i] = item
        else:
            # insert it
            self.items.insert(i, item)


    def __delitem__(self, key):
        """ Deletes a given keypoint """
        fkey = float(key)
        item = (fkey, 0)
        i = bisect_left(self.items, item)

        # convert IndexError to KeyError
        try:
            if self.items[i][0] == fkey:
                del self.items[i]
            else:
                raise KeyError("Key not found")
        except IndexError:
            raise KeyError("Key not found")

    def __len__(self):
        """ Returns the range of the indices """
        if len(self.items) > 0:
            return fabs(self.items[-1].index - self.items[0].index)
        else:
            return 0.0

    def __repr__(self):
        """ Formal description of the object """
        # Dump the contents into a dict style string
        lst = string.join([string.join( (str(i[0]), str(i[1]) ), ":") for i in self.items], ",")
        # spit the whole thing out
        return "%s(data={%s})" % (type(self).__name__, lst)

    def __iter__(self):
        """ Returns an iterator which can traverse the list """
        return self.items.__iter__()

